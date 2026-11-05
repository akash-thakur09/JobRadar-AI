"""Unit tests for MockEmailProvider and SmtpEmailProvider implementations."""

from unittest.mock import MagicMock, patch

import pytest

from app.modules.notifications.email.exceptions import (
    EmailAuthenticationError,
    EmailConnectionError,
    EmailTimeoutError,
)
from app.modules.notifications.email.factory import (
    get_email_provider,
    set_email_provider_override,
)
from app.modules.notifications.email.mock_provider import MockEmailProvider
from app.modules.notifications.email.protocol import (
    EmailAttachment,
    EmailMessage,
)
from app.modules.notifications.email.smtp_provider import SmtpEmailProvider


@pytest.fixture
def sample_message() -> EmailMessage:
    """Fixture returning sample email message."""
    return EmailMessage(
        to="candidate@example.com",
        subject="Exciting Role: AI Systems Engineer",
        html_body="<p>Job Match Found</p>",
        text_body="Job Match Found",
        attachments=[
            EmailAttachment(
                filename="Resume.pdf",
                content=b"%PDF-1.4 test binary content",
                content_type="application/pdf",
            )
        ],
    )


@pytest.mark.unit
async def test_mock_email_provider_success(sample_message: EmailMessage):
    """MockEmailProvider records dispatched messages and returns valid provider_message_id."""
    provider = MockEmailProvider()

    assert await provider.ping() is True
    assert provider.sent_count == 0

    result = await provider.send_email(sample_message)

    assert result.success is True
    assert result.provider_message_id is not None
    assert result.provider_message_id.startswith("<mock-")
    assert provider.sent_count == 1
    assert provider.last_message == sample_message
    assert len(provider.last_message.attachments) == 1

    provider.clear()
    assert provider.sent_count == 0


@pytest.mark.unit
async def test_mock_email_provider_simulated_failures(sample_message: EmailMessage):
    """MockEmailProvider simulates timeouts, connection errors, and authentication errors."""
    # Timeout
    timeout_provider = MockEmailProvider(simulate_timeout=True)
    with pytest.raises(EmailTimeoutError, match="timeout"):
        await timeout_provider.send_email(sample_message)

    # Connection error
    conn_provider = MockEmailProvider(simulate_connection_error=True)
    with pytest.raises(EmailConnectionError, match="connection refusal"):
        await conn_provider.send_email(sample_message)

    # Auth error
    auth_provider = MockEmailProvider(simulate_auth_error=True)
    with pytest.raises(EmailAuthenticationError, match="authentication rejection"):
        await auth_provider.send_email(sample_message)

    # Controlled failure result (non-exceptional)
    fail_provider = MockEmailProvider(simulate_failure=True, failure_error_message="Mailbox full")
    result = await fail_provider.send_email(sample_message)
    assert result.success is False
    assert result.error == "Mailbox full"


@pytest.mark.unit
async def test_smtp_email_provider_success(sample_message: EmailMessage):
    """SmtpEmailProvider formats MIME message and sends via SMTP."""
    provider = SmtpEmailProvider(
        host="smtp.example.com",
        port=587,
        username="user1",
        password="secretpassword",
        use_tls=True,
    )

    mock_smtp_instance = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_smtp_instance) as mock_smtp_cls:
        # Context manager support
        mock_smtp_instance.__enter__.return_value = mock_smtp_instance
        result = await provider.send_email(sample_message)

        assert result.success is True
        assert result.provider_message_id is not None
        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=15.0)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("user1", "secretpassword")
        mock_smtp_instance.send_message.assert_called_once()


@pytest.mark.unit
async def test_smtp_email_provider_error_mappings(sample_message: EmailMessage):
    """SmtpEmailProvider cleanly maps smtplib and socket exceptions to domain exceptions."""
    provider = SmtpEmailProvider(host="smtp.example.com", port=25)

    # Connection timeout
    with patch("smtplib.SMTP", side_effect=TimeoutError("Socket timeout")):
        with pytest.raises(EmailTimeoutError, match="timed out"):
            await provider.send_email(sample_message)

    # Connection refused
    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Connection refused")):
        with pytest.raises(EmailConnectionError, match="Failed to connect"):
            await provider.send_email(sample_message)

    # Authentication error
    import smtplib

    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
    provider_with_auth = SmtpEmailProvider(
        host="smtp.example.com", port=587, username="u", password="p"
    )
    with patch("smtplib.SMTP", return_value=mock_smtp_instance):
        with pytest.raises(EmailAuthenticationError, match="authentication failure"):
            await provider_with_auth.send_email(sample_message)


@pytest.mark.unit
async def test_smtp_email_provider_ping():
    """SmtpEmailProvider ping verifies reachability via SMTP NOOP."""
    provider = SmtpEmailProvider(host="smtp.example.com", port=25)
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance

    with patch("smtplib.SMTP", return_value=mock_smtp_instance):
        assert await provider.ping() is True
        mock_smtp_instance.noop.assert_called_once()

    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Refused")):
        assert await provider.ping() is False


@pytest.mark.unit
def test_email_provider_factory():
    """Factory resolves configured provider, mock in testing, and respects overrides."""
    # By default in test environment, resolves to MockEmailProvider
    provider = get_email_provider()
    assert isinstance(provider, MockEmailProvider)

    # Test explicit override
    custom_mock = MockEmailProvider()
    set_email_provider_override(custom_mock)
    assert get_email_provider() is custom_mock

    # Clear override
    set_email_provider_override(None)
    assert get_email_provider() is not custom_mock
