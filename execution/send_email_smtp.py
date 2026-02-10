"""
Send email via SMTP.
Supports Gmail and other SMTP providers.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailSender:
    """Send emails via SMTP."""

    def __init__(self):
        self.host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.port = int(os.getenv('SMTP_PORT', 587))
        self.user = os.getenv('SMTP_USER')
        self.password = os.getenv('SMTP_APP_PASSWORD')

        if not all([self.user, self.password]):
            raise ValueError(
                "SMTP credentials not configured. "
                "Please set SMTP_USER and SMTP_APP_PASSWORD in .env file"
            )

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            from_name: Optional sender name

        Returns:
            True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name or self.user} <{self.user}>"
            msg['To'] = to_email

            # Attach plain text version
            msg.attach(MIMEText(body, 'plain'))

            # Attach HTML version if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            # Create secure context and send
            context = ssl.create_default_context()

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls(context=context)
                server.login(self.user, self.password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
            return False

    def validate_email(self, email: str) -> bool:
        """Basic email format validation."""
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None


def send_bulk_emails(
    recipients: list,
    subject: str,
    template_fn,
    delay_seconds: int = 3,
    dry_run: bool = False
) -> dict:
    """
    Send emails to multiple recipients.

    Args:
        recipients: List of dicts with recipient data
        subject: Email subject (can use {placeholders})
        template_fn: Function that takes recipient dict and returns email body
        delay_seconds: Delay between sends
        dry_run: If True, don't actually send

    Returns:
        Dict with sent, failed, and skipped counts
    """
    sender = EmailSender()
    results = {'sent': 0, 'failed': 0, 'skipped': 0}

    for recipient in recipients:
        email = recipient.get('email')

        if not email or not sender.validate_email(email):
            results['skipped'] += 1
            continue

        # Personalize subject
        personalized_subject = subject.format(**recipient)

        # Generate email body
        body = template_fn(recipient)

        if dry_run:
            print(f"[DRY RUN] Would send to {email}")
            print(f"  Subject: {personalized_subject}")
            print(f"  Body preview: {body[:100]}...")
            results['sent'] += 1
        else:
            if sender.send_email(email, personalized_subject, body):
                results['sent'] += 1
            else:
                results['failed'] += 1

        # Rate limiting delay
        if delay_seconds > 0:
            import time
            time.sleep(delay_seconds)

    return results


if __name__ == "__main__":
    # Quick test
    sender = EmailSender()

    # Validate configuration
    print(f"SMTP configured: {sender.user}@{sender.host}")

    # Test validation
    print(f"Valid emails:")
    print(f"  test@example.com: {sender.validate_email('test@example.com')}")
    print(f"  invalid: {sender.validate_email('invalid')}")
