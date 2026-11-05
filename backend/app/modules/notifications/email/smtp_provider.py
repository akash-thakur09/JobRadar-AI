"""SMTP Email Provider using standard library smtplib and email packages."""

import asyncio
import email.utils
import logging
import smtplib
from email.message import EmailMessage as PyEmailMessage

from app.modules.notifications.email.exceptions import (
    EmailAuthenticationError,
    EmailConnectionError,
    EmailProviderError,
    EmailTimeoutError,
)
from app.modules.notifications.email.protocol import (
    EmailDeliveryResult,
    EmailMessage,
)

logger = logging.getLogger(__name__)


class SmtpEmailProvider:
    """Outbound SMTP email provider supporting TLS, authentication, and attachments."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1025,
        username: str = "",
        password: str = "",
        from_email: str = "notifications@jobradar.ai",
        from_name: str = "JobRadar AI",
        use_tls: bool = False,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds

    async def ping(self) -> bool:
        """Verify reachability of the configured SMTP host."""
        return await asyncio.to_thread(self._sync_ping)

    def _sync_ping(self) -> bool:
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as server:
                server.noop()
            return True
        except Exception as exc:
            logger.debug(f"SMTP ping failed for {self.host}:{self.port}: {exc}")
            return False

    async def send_email(self, message: EmailMessage) -> EmailDeliveryResult:
        """Send email message asynchronously via threadpool worker."""
        return await asyncio.to_thread(self._sync_send, message)

    def _sync_send(self, message: EmailMessage) -> EmailDeliveryResult:
        """Synchronous SMTP transmission with attachment handling and robust exception mapping."""
        # 1. Build MIME multipart message
        msg = PyEmailMessage()
        msg["Subject"] = message.subject
        sender_email = message.from_email or self.from_email
        sender_name = message.from_name or self.from_name
        msg["From"] = email.utils.formataddr((sender_name, sender_email))
        msg["To"] = message.to
        msg["Date"] = email.utils.formatdate(localtime=True)
        message_id = email.utils.make_msgid(domain="jobradar.ai")
        msg["Message-ID"] = message_id

        # Plain text and HTML alternative body
        msg.set_content(message.text_body)
        msg.add_alternative(message.html_body, subtype="html")

        # Binary attachments (e.g. tailored resume PDF)
        for attachment in message.attachments:
            maintype = "application"
            subtype = "octet-stream"
            if "/" in attachment.content_type:
                parts = attachment.content_type.split("/", 1)
                maintype = parts[0]
                subtype = parts[1]

            msg.add_attachment(
                attachment.content,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.filename,
            )

        # 2. Transmit via SMTP
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as server:
                if self.use_tls:
                    server.starttls()

                if self.username and self.password:
                    server.login(self.username, self.password)

                server.send_message(msg)

            logger.info(
                f"Successfully sent email to {message.to} via SMTP (Message-ID: {message_id})"
            )
            return EmailDeliveryResult(
                success=True,
                provider_message_id=message_id,
                error=None,
            )

        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error(f"SMTP authentication rejected for user {self.username}: {auth_err}")
            raise EmailAuthenticationError(f"SMTP authentication failure: {auth_err}") from auth_err

        except TimeoutError as timeout_err:
            logger.warning(f"SMTP connection timeout to {self.host}:{self.port}: {timeout_err}")
            raise EmailTimeoutError(
                f"SMTP connection timed out after {self.timeout_seconds}s"
            ) from timeout_err

        except (OSError, ConnectionRefusedError, smtplib.SMTPConnectError) as conn_err:
            logger.warning(f"SMTP connection failed to {self.host}:{self.port}: {conn_err}")
            raise EmailConnectionError(
                f"Failed to connect to SMTP server: {conn_err}"
            ) from conn_err

        except smtplib.SMTPException as smtp_err:
            logger.error(f"SMTP protocol error during email dispatch to {message.to}: {smtp_err}")
            raise EmailProviderError(
                f"SMTP protocol error: {smtp_err}", retryable=True
            ) from smtp_err

        except Exception as exc:
            logger.error(f"Unhandled exception during SMTP email delivery: {exc}", exc_info=True)
            raise EmailProviderError(f"Unhandled delivery error: {exc}", retryable=False) from exc
