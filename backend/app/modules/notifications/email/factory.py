"""Factory for instantiating EmailProvider implementations."""

from app.core.config import get_settings
from app.modules.notifications.email.mock_provider import MockEmailProvider
from app.modules.notifications.email.protocol import EmailProvider
from app.modules.notifications.email.smtp_provider import SmtpEmailProvider

_override_provider: EmailProvider | None = None


def set_email_provider_override(provider: EmailProvider | None) -> None:
    """Set or clear a global test provider override."""
    global _override_provider
    _override_provider = provider


def get_email_provider() -> EmailProvider:
    """Obtain configured EmailProvider instance based on application settings."""
    if _override_provider is not None:
        return _override_provider

    settings = get_settings()
    if settings.email_provider.lower() == "mock" or settings.is_testing:
        return MockEmailProvider()

    return SmtpEmailProvider(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.effective_smtp_username,
        password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        from_name=settings.smtp_from_name,
        use_tls=settings.smtp_use_tls,
        timeout_seconds=settings.smtp_timeout_seconds,
    )

