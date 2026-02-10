"""
Email processor daemon - monitors Gmail and creates GHL contacts from lead emails.

This daemon:
1. Monitors Gmail inbox via IMAP for new emails
2. Extracts lead data using AI/regex
3. Creates/updates GoHighLevel contacts in SALES pipeline
4. Tracks processed emails to prevent duplicates

Usage:
    python email_processor.py

The daemon runs continuously and can be managed via systemd.
"""

import os
import sys
import time
import sqlite3
import logging
import signal
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Add parent directory to path for imports (ghl_api, google_calendar are in parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imap_client import IMAPClient, EmailMessage, IMAPConnectionError
from email_extractor import EmailExtractor
from ghl_api import GoHighLevelAPI
from models.lead_data import LeadData

load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv('EMAIL_PROCESSOR_LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CHECK_INTERVAL = int(os.getenv('EMAIL_PROCESSOR_CHECK_INTERVAL', '60'))  # seconds
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'processed_emails.db')


class ProcessedEmailTracker:
    """
    Track processed email UIDs in SQLite to prevent duplicate processing.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize tracker.

        Args:
            db_path: Path to SQLite database (created if needed)
        """
        self.db_path = db_path or DB_PATH

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    uid TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    email_from TEXT,
                    subject TEXT,
                    contact_id TEXT,
                    platform TEXT,
                    status TEXT DEFAULT 'success'
                )
            """)

            # Add index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at
                ON processed_emails(processed_at)
            """)

            conn.commit()

    def is_processed(self, uid: str) -> bool:
        """Check if an email UID has been processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_emails WHERE uid = ? LIMIT 1",
                (uid,)
            )
            return cursor.fetchone() is not None

    def mark_processed(
        self,
        uid: str,
        email_from: str = None,
        subject: str = None,
        contact_id: str = None,
        platform: str = None,
        status: str = 'success'
    ) -> None:
        """Mark an email as processed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processed_emails
                (uid, processed_at, email_from, subject, contact_id, platform, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (uid, datetime.now(timezone.utc).isoformat(), email_from, subject, contact_id, platform, status))
            conn.commit()

    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Remove old processed email records.

        Args:
            days: Keep records newer than this many days

        Returns:
            Number of records deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM processed_emails WHERE processed_at < ?",
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about processed emails."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT email_from) as unique_senders,
                    COUNT(DISTINCT platform) as platforms,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status != 'success' THEN 1 END) as failed
                FROM processed_emails
            """)
            row = cursor.fetchone()

            # Get platform breakdown
            cursor = conn.execute("""
                SELECT platform, COUNT(*) as count
                FROM processed_emails
                GROUP BY platform
                ORDER BY count DESC
            """)
            platforms = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                'total_processed': row[0],
                'unique_senders': row[1],
                'platforms_detected': row[2],
                'successful': row[3],
                'failed': row[4],
                'platform_breakdown': platforms
            }


class EmailProcessor:
    """
    Main email processor daemon.

    Monitors Gmail for new lead emails and creates GHL contacts.
    """

    def __init__(self):
        """Initialize processor with all dependencies."""
        logger.info("Initializing EmailProcessor...")

        self.imap_client = IMAPClient()
        self.extractor = EmailExtractor()
        self.ghl_api = GoHighLevelAPI()
        self.tracker = ProcessedEmailTracker()

        # Metrics
        self.metrics = {
            'emails_processed': 0,
            'leads_created': 0,
            'leads_updated': 0,
            'extraction_failures': 0,
            'ghl_failures': 0,
            'start_time': datetime.now(timezone.utc),
            'last_check': None,
        }

        # Control flag for graceful shutdown
        self._running = True

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("EmailProcessor initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False

    def find_existing_contact(self, lead: LeadData) -> Optional[Dict[str, Any]]:
        """
        Search for existing contact in GHL using multiple strategies.

        Args:
            lead: LeadData to search for

        Returns:
            Existing contact dict or None
        """
        # Strategy 1: Search by email (primary)
        if lead.email:
            try:
                result = self.ghl_api.search_contacts(lead.email)
                contacts = result.get('contacts', [])
                if contacts:
                    # Find exact email match
                    for contact in contacts:
                        if contact.get('email', '').lower() == lead.email.lower():
                            logger.info(f"Found existing contact by email: {contact.get('id')}")
                            return contact
            except Exception as e:
                logger.warning(f"GHL search by email failed: {e}")

        # Strategy 2: Search by phone (secondary)
        if lead.phone:
            try:
                result = self.ghl_api.search_contacts(lead.phone)
                contacts = result.get('contacts', [])
                if contacts:
                    logger.info(f"Found existing contact by phone: {contacts[0].get('id')}")
                    return contacts[0]
            except Exception as e:
                logger.warning(f"GHL search by phone failed: {e}")

        # Strategy 3: Search by name + wedding date (tertiary)
        if lead.name and lead.wedding_date:
            try:
                query = f"{lead.name} {lead.wedding_date}"
                result = self.ghl_api.search_contacts(query)
                contacts = result.get('contacts', [])
                if contacts:
                    logger.info(f"Found existing contact by name+date: {contacts[0].get('id')}")
                    return contacts[0]
            except Exception as e:
                logger.warning(f"GHL search by name+date failed: {e}")

        return None

    def create_sales_opportunity(self, lead: LeadData, contact_id: str) -> bool:
        """
        Create an opportunity in the SALES pipeline for a contact.

        Args:
            lead: LeadData with name and wedding info
            contact_id: GHL contact ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get SALES pipeline ID
            pipeline_id = self.ghl_api.get_pipeline_id_by_name("1. SALES")
            if not pipeline_id:
                # Try alternative names
                pipeline_id = self.ghl_api.get_pipeline_id_by_name("SALES")
                if not pipeline_id:
                    pipeline_id = self.ghl_api.get_pipeline_id_by_name("Sales")

            if not pipeline_id:
                logger.warning(f"Could not find SALES pipeline")
                return False

            # Get "New Leads" stage ID
            stage_id = self.ghl_api.get_pipeline_stage_id_by_name(pipeline_id, "New Leads")
            if not stage_id:
                # Try alternative stage names
                stage_id = self.ghl_api.get_pipeline_stage_id_by_name(pipeline_id, "New Lead")
                if not stage_id:
                    # Try to get the first stage as fallback
                    import requests
                    url = f"{self.ghl_api.base_url}/opportunities/pipelines/{pipeline_id}"
                    params = {"locationId": self.ghl_api.location_id}
                    response = requests.get(url, headers=self.ghl_api.headers, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        stages = data.get("stages", [])
                        if stages:
                            stage_id = stages[0].get("id")
                            logger.info(f"Using first stage as fallback: {stages[0].get('name')}")

            if not stage_id:
                logger.warning(f"Could not find any stage in SALES pipeline")
                return False

            # Generate opportunity title
            opportunity_title = self.generate_opportunity_title(lead)

            # Create the opportunity
            opp_result = self.ghl_api.create_opportunity(
                pipeline_id=pipeline_id,
                stage_id=stage_id,
                contact_id=contact_id,
                title=opportunity_title,
                status="open"
            )
            logger.info(f"Created opportunity '{opportunity_title}' in SALES pipeline (ID: {opp_result.get('opportunity', {}).get('id')})")
            return True

        except Exception as e:
            logger.error(f"Failed to create opportunity: {e}")
            return False

    def generate_opportunity_title(self, lead: LeadData) -> str:
        """
        Generate opportunity title from lead data.

        Format: "Bride & Groom's Wedding" or "Name's Wedding" if only one name

        Args:
            lead: LeadData with name and optionally partner_name

        Returns:
            Opportunity title
        """
        # If we have both names, use "Bride & Groom's Wedding"
        if lead.name and lead.partner_name:
            # Extract first names
            bride_first = lead.name.split()[0] if lead.name else "Client"
            groom_first = lead.partner_name.split()[0] if lead.partner_name else "Partner"
            return f"{bride_first} & {groom_first}'s Wedding"
        elif lead.name:
            # Use just the lead's name
            first_name = lead.name.split()[0]
            return f"{first_name}'s Wedding"
        else:
            return "New Wedding Inquiry"

    def create_or_update_contact(self, lead: LeadData) -> Dict[str, Any]:
        """
        Create or update GHL contact from lead data.

        Args:
            lead: LeadData to sync to GHL

        Returns:
            Dict with action, contact_id, and status
        """
        existing = self.find_existing_contact(lead)

        first_name, last_name = lead.split_name()

        if existing:
            # Update existing contact
            contact_id = existing.get('id')

            try:
                # Build custom fields update
                custom_fields = lead.to_ghl_custom_fields()

                # Update with new custom field values
                self.ghl_api.update_contact(contact_id, custom_fields)

                # Also update basic fields if provided
                if lead.email and existing.get('email') != lead.email:
                    # Note: GHL API might not allow direct email update via custom fields
                    # This may need additional API calls
                    pass

                self.metrics['leads_updated'] += 1
                logger.info(f"Updated contact {contact_id} for {lead.name}")

                # Check if contact has an opportunity in SALES pipeline, if not create one
                try:
                    # Search for opportunities with this contact
                    pipeline_id = self.ghl_api.get_pipeline_id_by_name("SALES")
                    if not pipeline_id:
                        pipeline_id = self.ghl_api.get_pipeline_id_by_name("1. SALES")

                    if pipeline_id:
                        # Always create the opportunity - if it already exists with the same title,
                        # GHL will return an error which we catch and ignore
                        logger.info(f"Creating opportunity for existing contact {contact_id}")
                        try:
                            self.create_sales_opportunity(lead, contact_id)
                        except Exception as opp_error:
                            logger.debug(f"Opportunity may already exist: {opp_error}")

                except Exception as e:
                    logger.warning(f"Could not check/create opportunity: {e}")

                return {
                    'action': 'updated',
                    'contact_id': contact_id,
                    'status': 'success'
                }

            except Exception as e:
                logger.error(f"Failed to update contact {contact_id}: {e}")
                self.metrics['ghl_failures'] += 1
                return {
                    'action': 'update_failed',
                    'contact_id': contact_id,
                    'status': 'error',
                    'error': str(e)
                }

        else:
            # Create new contact AND opportunity
            try:
                custom_fields = lead.to_ghl_custom_fields()

                result = self.ghl_api.create_contact(
                    email=lead.email or f"noemail-{datetime.now(timezone.utc).timestamp()}@placeholder.com",
                    first_name=first_name,
                    last_name=last_name,
                    phone=lead.phone or '',
                    custom_fields=custom_fields
                )

                contact_id = result.get('contact', {}).get('id')
                self.metrics['leads_created'] += 1
                logger.info(f"Created new contact {contact_id} for {lead.name}")

                # Create opportunity in SALES pipeline
                self.create_sales_opportunity(lead, contact_id)

                return {
                    'action': 'created',
                    'contact_id': contact_id,
                    'status': 'success'
                }

            except Exception as e:
                logger.error(f"Failed to create contact: {e}")
                self.metrics['ghl_failures'] += 1
                return {
                    'action': 'create_failed',
                    'status': 'error',
                    'error': str(e)
                }

    def process_email(self, email_msg: EmailMessage) -> Dict[str, Any]:
        """
        Process a single email message.

        Args:
            email_msg: EmailMessage to process

        Returns:
            Processing result dict
        """
        uid = email_msg.uid

        # Skip if already processed
        if self.tracker.is_processed(uid):
            logger.debug(f"Email {uid} already processed, skipping")
            return {
                'status': 'skipped',
                'reason': 'already_processed'
            }

        logger.info(f"Processing email {uid}: {email_msg.subject}")

        # Extract lead data
        lead = self.extractor.extract(
            email_text=email_msg.body,
            from_addr=email_msg.from_addr,
            subject=email_msg.subject,
            headers=email_msg.raw_headers
        )

        if not lead or not lead.is_valid():
            logger.warning(f"Failed to extract valid lead from email {uid}")
            self.metrics['extraction_failures'] += 1
            self.tracker.mark_processed(
                uid,
                email_from=email_msg.from_addr,
                subject=email_msg.subject,
                status='extraction_failed'
            )
            return {
                'status': 'failed',
                'reason': 'extraction_failed'
            }

        # Create/update GHL contact
        result = self.create_or_update_contact(lead)

        # Mark as processed
        self.tracker.mark_processed(
            uid,
            email_from=email_msg.from_addr,
            subject=email_msg.subject,
            contact_id=result.get('contact_id'),
            platform=lead.source_platform,
            status=result.get('status', 'success')
        )

        self.metrics['emails_processed'] += 1

        logger.info(f"Completed processing email {uid}: {result}")
        return result

    def check_new_emails(self) -> int:
        """
        Check for and process new emails.

        Returns:
            Number of emails processed
        """
        self.metrics['last_check'] = datetime.now(timezone.utc)

        try:
            # Fetch unseen emails
            emails = self.imap_client.fetch_new_emails()

            if not emails:
                logger.debug("No new emails found")
                return 0

            logger.info(f"Found {len(emails)} new emails to process")

            # Process each email
            for email_msg in emails:
                if not self._running:
                    break
                self.process_email(email_msg)

            return len(emails)

        except IMAPConnectionError as e:
            logger.error(f"IMAP connection error: {e}")
            # Will attempt reconnection on next check
            return 0

        except Exception as e:
            logger.error(f"Error checking emails: {e}", exc_info=True)
            return 0

    def run(self) -> None:
        """
        Main daemon loop.

        Continuously checks for new emails at the configured interval.
        """
        logger.info("Starting EmailProcessor daemon...")
        logger.info(f"Check interval: {CHECK_INTERVAL} seconds")

        # Initial connection
        try:
            self.imap_client.connect()
        except IMAPConnectionError as e:
            logger.error(f"Failed to establish initial IMAP connection: {e}")
            return

        # Main loop
        while self._running:
            try:
                # Check for new emails
                count = self.check_new_emails()

                # Log summary periodically
                if count > 0:
                    self.log_metrics()

                # Wait before next check
                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                time.sleep(CHECK_INTERVAL)

        # Cleanup
        logger.info("Shutting down EmailProcessor...")
        self.log_metrics()
        self.imap_client.close()

    def log_metrics(self) -> None:
        """Log current metrics."""
        uptime = (datetime.now(timezone.utc) - self.metrics['start_time']).total_seconds()

        logger.info(
            f"Metrics - "
            f"Processed: {self.metrics['emails_processed']}, "
            f"Created: {self.metrics['leads_created']}, "
            f"Updated: {self.metrics['leads_updated']}, "
            f"Extraction failures: {self.metrics['extraction_failures']}, "
            f"GHL failures: {self.metrics['ghl_failures']}, "
            f"Uptime: {uptime:.0f}s"
        )

        # Also log tracker stats
        try:
            stats = self.tracker.get_stats()
            logger.info(
                f"Tracker stats - "
                f"Total DB: {stats['total_processed']}, "
                f"Platforms: {stats['platform_breakdown']}"
            )
        except Exception as e:
            logger.warning(f"Could not fetch tracker stats: {e}")

    def run_once(self) -> None:
        """
        Run a single check and exit.

        Useful for testing and one-off processing.
        """
        logger.info("Running single email check...")

        try:
            self.imap_client.connect()
            count = self.check_new_emails()
            self.log_metrics()

            logger.info(f"Check complete. Processed {count} emails.")

        finally:
            self.imap_client.close()


def main():
    """Main entry point."""
    # Check for --once flag
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        processor = EmailProcessor()
        processor.run_once()
    else:
        processor = EmailProcessor()
        processor.run()


if __name__ == "__main__":
    main()
