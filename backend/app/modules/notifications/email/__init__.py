"""Email provider subsystem package."""

from app.modules.notifications.email.factory import (
    get_email_provider,
    set_email_provider_override,
)
from app.modules.notifications.email.mock_provider import MockEmailProvider
from app.modules.notifications.email.protocol import (
    EmailAttachment,
    EmailDeliveryResult,
    EmailMessage,
    EmailProvider,
)
from app.modules.notifications.email.smtp_provider import SmtpEmailProvider

__all__ = [
    "EmailAttachment",
    "EmailDeliveryResult",
    "EmailMessage",
    "EmailProvider",
    "MockEmailProvider",
    "SmtpEmailProvider",
    "get_email_provider",
    "set_email_provider_override",
]

