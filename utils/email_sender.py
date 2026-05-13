"""
utils/email_sender.py
────────────────────────────────────────────────────────────────────────────────
Sends generated emails via SMTP (Gmail / any provider).
Supports dry-run mode for testing without actually sending.

Security: credentials are read from config (env vars) only — never hardcoded.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional

from utils.config import config
from utils.email_generator import GeneratedEmail

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    invoice_id: str
    recipient_email: str
    success: bool
    error: Optional[str] = None
    dry_run: bool = False


class EmailSender:
    """
    Sends follow-up emails via SMTP.

    Parameters:
        dry_run: If True, emails are formatted but never actually sent.
                 Use this in development / demo mode.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._smtp_configured = bool(config.EMAIL_USER and config.EMAIL_PASSWORD)

    def _build_message(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> MIMEMultipart:
        """Build a MIME email message."""
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Plain text version
        text_part = MIMEText(body, "plain", "utf-8")

        # Basic HTML version (preserves line breaks)
        html_body = body.replace("\n", "<br>")
        html_content = f"""
        <html><body style="font-family: Arial, sans-serif; font-size: 14px; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <p>{html_body}</p>
        </body></html>
        """
        html_part = MIMEText(html_content, "html", "utf-8")

        msg.attach(text_part)
        msg.attach(html_part)
        return msg

    def send(
        self,
        to_email: str,
        generated_email: GeneratedEmail,
    ) -> SendResult:
        """Send a single generated email."""
        if not generated_email.is_successful:
            return SendResult(
                invoice_id=generated_email.invoice_id,
                recipient_email=to_email,
                success=False,
                error="Email generation failed; nothing to send",
                dry_run=self.dry_run,
            )

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would send to %s | Subject: %s",
                to_email, generated_email.subject
            )
            return SendResult(
                invoice_id=generated_email.invoice_id,
                recipient_email=to_email,
                success=True,
                dry_run=True,
            )

        if not self._smtp_configured:
            return SendResult(
                invoice_id=generated_email.invoice_id,
                recipient_email=to_email,
                success=False,
                error="SMTP not configured (EMAIL_USER / EMAIL_PASSWORD missing)",
                dry_run=False,
            )

        try:
            msg = self._build_message(
                to_email=to_email,
                subject=generated_email.subject,
                body=generated_email.body,
            )
            with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
                server.sendmail(config.EMAIL_USER, to_email, msg.as_string())

            logger.info("Email sent to %s for invoice %s", to_email, generated_email.invoice_id)
            return SendResult(
                invoice_id=generated_email.invoice_id,
                recipient_email=to_email,
                success=True,
                dry_run=False,
            )
        except smtplib.SMTPException as exc:
            logger.error("SMTP error sending to %s: %s", to_email, exc)
            return SendResult(
                invoice_id=generated_email.invoice_id,
                recipient_email=to_email,
                success=False,
                error=str(exc),
                dry_run=False,
            )
