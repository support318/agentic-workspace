"""
IMAP client wrapper with IDLE support and reconnection logic.

This module provides a robust IMAP client for monitoring Gmail inbox
for new lead emails. Features include:
- Automatic reconnection with exponential backoff
- IMAP IDLE support for real-time notifications
- Email fetching by UID
- Connection health monitoring
"""

import imaplib
import email as email_module
import email.header
import email.message
import time
import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Simple container for fetched email data."""
    uid: str
    subject: str
    from_addr: str
    to_addr: str
    date: datetime
    body: str
    html_body: Optional[str] = None
    raw_headers: Dict[str, str] = None

    def __post_init__(self):
        if self.raw_headers is None:
            self.raw_headers = {}


class IMAPConnectionError(Exception):
    """Raised when IMAP connection fails."""
    pass


class IMAPClient:
    """
    IMAP client with reconnection and IDLE support.

    Usage:
        client = IMAPClient()
        client.connect()

        # Fetch new emails
        for email_msg in client.fetch_new_emails():
            process_email(email_msg)

        # Or use IDLE for real-time monitoring
        for email_msg in client.idle_wait():
            process_email(email_msg)
    """

    # Default configuration
    DEFAULT_SERVER = "imap.gmail.com"
    DEFAULT_PORT = 993
    DEFAULT_FOLDER = "INBOX"

    # Reconnection settings
    MAX_RECONNECT_ATTEMPTS = 5
    BASE_RETRY_DELAY = 2  # seconds

    # Timeout settings
    SOCKET_TIMEOUT = 30  # seconds
    IDLE_TIMEOUT = 10  # minutes (max Gmail IDLE duration)

    def __init__(
        self,
        email_address: Optional[str] = None,
        app_password: Optional[str] = None,
        server: Optional[str] = None,
        port: Optional[int] = None
    ):
        """
        Initialize IMAP client.

        Args:
            email_address: Gmail address (defaults to IMAP_EMAIL env var)
            app_password: Google App Password (defaults to IMAP_APP_PASSWORD env var)
            server: IMAP server (defaults to IMAP_SERVER env var or imap.gmail.com)
            port: IMAP port (defaults to IMAP_PORT env var or 993)
        """
        self.email_address = email_address or os.getenv('IMAP_EMAIL')
        self.app_password = app_password or os.getenv('IMAP_APP_PASSWORD')
        self.server = server or os.getenv('IMAP_SERVER', self.DEFAULT_SERVER)
        self.port = port or int(os.getenv('IMAP_PORT', str(self.DEFAULT_PORT)))

        if not self.email_address:
            raise ValueError("IMAP_EMAIL not configured")
        if not self.app_password:
            raise ValueError("IMAP_APP_PASSWORD not configured")

        self.connection: Optional[imaplib.IMAP4_SSL] = None
        self._current_folder: Optional[str] = None
        self._is_idle = False

        logger.info(
            f"IMAPClient initialized for {self.email_address} "
            f"({self.server}:{self.port})"
        )

    def connect(self, attempt: int = 1) -> imaplib.IMAP4_SSL:
        """
        Establish IMAP connection with retry logic.

        Args:
            attempt: Current attempt number (for recursion)

        Returns:
            Connected IMAP4_SSL instance

        Raises:
            IMAPConnectionError: If all reconnection attempts fail
        """
        if self.connection and self._is_connected():
            return self.connection

        try:
            logger.info(f"Connecting to IMAP server (attempt {attempt}/{self.MAX_RECONNECT_ATTEMPTS})...")

            # Create SSL connection
            self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            self.connection.socket().settimeout(self.SOCKET_TIMEOUT)

            # Login
            self.connection.login(self.email_address, self.app_password)
            logger.info(f"Successfully logged in as {self.email_address}")

            # Select inbox
            self.select_folder(self.DEFAULT_FOLDER)

            return self.connection

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection failed: {e}")

            if attempt < self.MAX_RECONNECT_ATTEMPTS:
                # Exponential backoff
                delay = self.BASE_RETRY_DELAY * (2 ** (attempt - 1))
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                return self.connect(attempt + 1)
            else:
                raise IMAPConnectionError(
                    f"Failed to connect after {self.MAX_RECONNECT_ATTEMPTS} attempts"
                )

        except Exception as e:
            logger.error(f"Unexpected error during IMAP connection: {e}")
            raise IMAPConnectionError(f"Connection error: {e}")

    def _is_connected(self) -> bool:
        """Check if connection is alive."""
        if not self.connection:
            return False

        try:
            # NOOP is a lightweight way to check connection
            self.connection.noop()
            return True
        except (imaplib.IMAP4.error, OSError):
            return False

    def ensure_connected(self) -> None:
        """Ensure we have a valid connection, reconnecting if necessary."""
        if not self._is_connected():
            logger.warning("Connection lost, attempting to reconnect...")
            self.connect()

    def select_folder(self, folder: str) -> None:
        """
        Select a mailbox folder.

        Args:
            folder: Folder name (e.g., 'INBOX')
        """
        self.ensure_connected()
        try:
            self.connection.select(folder)
            self._current_folder = folder
            logger.debug(f"Selected folder: {folder}")
        except imaplib.IMAP4.error as e:
            logger.error(f"Failed to select folder {folder}: {e}")
            raise

    def search_unseen(self) -> List[str]:
        """
        Search for unseen emails in current folder.

        Returns:
            List of UIDs (as strings)
        """
        self.ensure_connected()

        try:
            # Search for unseen messages
            status, messages = self.connection.search(None, 'UNSEEN')

            if status != 'OK':
                logger.error(f"IMAP search failed with status: {status}")
                return []

            if not messages[0]:
                return []

            # Return list of message IDs (not UIDs yet)
            return messages[0].split()

        except imaplib.IMAP4.error as e:
            logger.error(f"Search failed: {e}")
            # Try reconnecting
            self.connect()
            return []

    def fetch_by_uid(self, uid: str) -> Optional[EmailMessage]:
        """
        Fetch a single email by UID.

        Args:
            uid: Message UID

        Returns:
            EmailMessage or None if fetch fails
        """
        self.ensure_connected()

        try:
            # Fetch message body
            status, msg_data = self.connection.fetch(uid, '(RFC822)')

            if status != 'OK' or not msg_data[0]:
                logger.error(f"Failed to fetch message UID {uid}")
                return None

            # Parse email
            raw_email = msg_data[0][1]
            email_message = email_module.message_from_bytes(raw_email)

            # Extract data
            subject = self._decode_header(email_message.get('Subject', ''))
            from_addr = self._decode_header(email_message.get('From', ''))
            to_addr = self._decode_header(email_message.get('To', ''))
            date_str = email_message.get('Date', '')
            try:
                date = email_module.utils.parsedate_to_datetime(date_str) if date_str else datetime.now(timezone.utc)
            except (TypeError, ValueError, IndexError):
                # Some emails have malformed dates
                date = datetime.now(timezone.utc)

            # Extract body
            body, html_body = self._extract_body(email_message)

            # Extract headers
            raw_headers = dict(email_message.items())

            return EmailMessage(
                uid=uid,
                subject=subject,
                from_addr=from_addr,
                to_addr=to_addr,
                date=date,
                body=body,
                html_body=html_body,
                raw_headers=raw_headers
            )

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error fetching UID {uid}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing email UID {uid}: {e}")
            return None

    def fetch_new_emails(self) -> List[EmailMessage]:
        """
        Fetch all currently unseen emails.

        Returns:
            List of EmailMessage objects
        """
        self.ensure_connected()

        # Get UIDs of unseen messages
        message_ids = self.search_unseen()

        if not message_ids:
            return []

        # Fetch each message
        emails = []
        for msg_id in message_ids:
            msg = self.fetch_by_uid(msg_id)
            if msg:
                emails.append(msg)

        logger.info(f"Fetched {len(emails)} new emails")
        return emails

    def idle_wait(self, timeout_minutes: int = None) -> List[EmailMessage]:
        """
        Wait for new emails using IMAP IDLE.

        Args:
            timeout_minutes: How long to wait (default: IDLE_TIMEOUT)

        Returns:
            List of new EmailMessage objects when they arrive
        """
        timeout_minutes = timeout_minutes or self.IDLE_TIMEOUT
        timeout_seconds = timeout_minutes * 60

        self.ensure_connected()
        self._is_idle = True

        try:
            # Start IDLE mode
            logger.debug("Starting IMAP IDLE...")
            self.connection.idle()

            # Wait for response
            start_time = time.time()
            new_emails = []

            while time.time() - start_time < timeout_seconds:
                try:
                    # Wait for IDLE response with short timeout
                    self.connection.wait(timeout=10)

                    # Check for new messages
                    new_emails = self.fetch_new_emails()
                    if new_emails:
                        break

                except imaplib.IMAP4.abort:
                    # Connection lost, reconnect
                    logger.warning("IDLE connection lost, reconnecting...")
                    self._is_idle = False
                    self.connect()
                    continue

                except KeyboardInterrupt:
                    logger.info("IDLE interrupted by user")
                    break

            return new_emails

        finally:
            self._is_idle = False
            # End IDLE mode
            try:
                self.connection.idle_done()
                logger.debug("Ended IMAP IDLE")
            except (imaplib.IMAP4.error, AttributeError):
                pass

    def mark_as_seen(self, uid: str) -> bool:
        """
        Mark an email as seen/read.

        Args:
            uid: Message UID

        Returns:
            True if successful
        """
        self.ensure_connected()
        try:
            self.connection.store(uid, '+FLAGS', '\\Seen')
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"Failed to mark UID {uid} as seen: {e}")
            return False

    def get_uids_since(self, date: datetime) -> List[str]:
        """
        Get all UIDs for emails since a given date.

        Args:
            date: Start date for search

        Returns:
            List of UIDs
        """
        self.ensure_connected()

        # Format date for IMAP search
        date_str = date.strftime('%d-%b-%Y')

        try:
            status, messages = self.connection.search(
                None,
                f'SINCE {date_str}'
            )

            if status != 'OK':
                return []

            return messages[0].split() if messages[0] else []

        except imaplib.IMAP4.error as e:
            logger.error(f"Failed to search UIDs since {date_str}: {e}")
            return []

    def _decode_header(self, header: str) -> str:
        """
        Decode email header, handling various encodings.

        Args:
            header: Raw header string

        Returns:
            Decoded Unicode string
        """
        if not header:
            return ""

        decoded_parts = []

        for part, encoding in email.header.decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                except (LookupError, UnicodeDecodeError):
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(str(part))

        return ''.join(decoded_parts)

    def _extract_body(self, email_message: email_module.message.Message) -> Tuple[str, Optional[str]]:
        """
        Extract plain text and HTML body from email.

        Args:
            email_message: Email message object

        Returns:
            Tuple of (plain_text_body, html_body)
        """
        plain_text = ""
        html_text = None

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                # Skip attachments
                if 'attachment' in content_disposition:
                    continue

                if content_type == 'text/plain':
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        plain_text = part.get_payload(decode=True).decode(charset, errors='replace')
                    except (LookupError, UnicodeDecodeError):
                        plain_text = part.get_payload(decode=True).decode('utf-8', errors='replace')

                elif content_type == 'text/html':
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        html_text = part.get_payload(decode=True).decode(charset, errors='replace')
                    except (LookupError, UnicodeDecodeError):
                        html_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
        else:
            # Not multipart
            content_type = email_message.get_content_type()
            charset = email_message.get_content_charset() or 'utf-8'

            try:
                payload = email_message.get_payload(decode=True).decode(charset, errors='replace')
            except (LookupError, UnicodeDecodeError):
                payload = email_message.get_payload(decode=True).decode('utf-8', errors='replace')

            if content_type == 'text/html':
                html_text = payload
                plain_text = self._html_to_text(payload)
            else:
                plain_text = payload

        return plain_text, html_text

    def _html_to_text(self, html: str) -> str:
        """
        Simple HTML to text conversion.

        Args:
            html: HTML string

        Returns:
            Plain text
        """
        import re

        # Remove script and style elements
        html = re.sub(r'<script[^>]*?>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*?>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert common tags
        html = re.sub(r'<br[^>]*>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</p>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</div>', '\n', html, flags=re.IGNORECASE)

        # Remove all remaining tags
        html = re.sub(r'<[^>]+>', '', html)

        # Decode HTML entities
        html = html.replace('&nbsp;', ' ')
        html = html.replace('&amp;', '&')
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&quot;', '"')
        html = html.replace('&#39;', "'")

        # Clean up whitespace
        lines = [line.strip() for line in html.split('\n')]
        return '\n'.join(line for line in lines if line)

    def close(self) -> None:
        """Close the IMAP connection."""
        if self._is_idle:
            try:
                self.connection.idle_done()
            except (imaplib.IMAP4.error, AttributeError):
                pass
            self._is_idle = False

        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("IMAP connection closed")
            except (imaplib.IMAP4.error, AttributeError):
                pass
            finally:
                self.connection = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Test the IMAP client
    logging.basicConfig(level=logging.DEBUG)

    try:
        client = IMAPClient()
        client.connect()

        # Fetch unseen emails
        emails = client.fetch_new_emails()

        print(f"\nFound {len(emails)} new emails:")
        for msg in emails:
            print(f"\nFrom: {msg.from_addr}")
            print(f"Subject: {msg.subject}")
            print(f"Date: {msg.date}")
            print(f"UID: {msg.uid}")
            print(f"Body preview: {msg.body[:200]}...")

        client.close()

    except IMAPConnectionError as e:
        print(f"Connection error: {e}")
