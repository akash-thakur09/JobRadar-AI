"""Mock Email Provider for deterministic testing without external SMTP server dependency."""

import uuid

from app.modules.notifications.email.exceptions import (
    EmailAuthenticationError,
    EmailConnectionError,
    EmailTimeoutError,
)
from app.modules.notifications.email.protocol import (
    EmailDeliveryResult,
    EmailMessage,
)


class MockEmailProvider:
    """Deterministic in-memory email provider for unit and integration testing."""

    def __init__(
        self,
        simulate_timeout: bool = False,
        simulate_connection_error: bool = False,
        simulate_auth_error: bool = False,
        simulate_failure: bool = False,
        failure_error_message: str = "Simulated delivery failure",
        simulate_exception: Exception | None = None,
        is_healthy: bool = True,
    ) -> None:
        self.simulate_timeout = simulate_timeout
        self.simulate_connection_error = simulate_connection_error
        self.simulate_auth_error = simulate_auth_error
        self.simulate_failure = simulate_failure
        self.failure_error_message = failure_error_message
        self.simulate_exception = simulate_exception
        self.is_healthy = is_healthy
        self.sent_messages: list[EmailMessage] = []

    async def ping(self) -> bool:
        """Return simulated reachability state."""
        return self.is_healthy

    async def send_email(self, message: EmailMessage) -> EmailDeliveryResult:
        """Record email delivery attempt or trigger programmed failure mode."""
        if self.simulate_exception is not None:
            raise self.simulate_exception

        if self.simulate_timeout:
            raise EmailTimeoutError("Simulated email delivery timeout.")

        if self.simulate_connection_error:
            raise EmailConnectionError("Simulated connection refusal to SMTP server.")

        if self.simulate_auth_error:
            raise EmailAuthenticationError("Simulated SMTP authentication rejection.")

        if self.simulate_failure:
            return EmailDeliveryResult(
                success=False,
                error=self.failure_error_message,
            )

        # Record successful dispatch
        self.sent_messages.append(message)
        message_id = f"<mock-{uuid.uuid4().hex[:12]}@jobradar.ai>"
        return EmailDeliveryResult(
            success=True,
            provider_message_id=message_id,
            error=None,
        )

    @property
    def sent_count(self) -> int:
        """Return total count of successfully dispatched messages."""
        return len(self.sent_messages)

    @property
    def last_message(self) -> EmailMessage | None:
        """Return the most recently dispatched email message."""
        return self.sent_messages[-1] if self.sent_messages else None

    def clear(self) -> None:
        """Reset sent messages history."""
        self.sent_messages.clear()
