"""Exceptions for email delivery provider implementations."""

from app.core.exceptions import InfrastructureException


class EmailProviderError(InfrastructureException):
    """Base exception for all email delivery and infrastructure failures."""

    def __init__(
        self,
        message: str,
        status_code: int = 503,
        error_type: str = "email-provider-error",
        retryable: bool = False,
    ) -> None:
        super().__init__(message=message, status_code=status_code, error_type=error_type)
        self.retryable = retryable


class EmailTimeoutError(EmailProviderError):
    """Raised when connecting or transmitting to the email provider times out (retryable)."""

    def __init__(self, message: str = "Email transmission timed out.") -> None:
        super().__init__(
            message=message,
            status_code=504,
            error_type="email-timeout",
            retryable=True,
        )


class EmailConnectionError(EmailProviderError):
    """Raised when network connection to the SMTP server fails (retryable)."""

    def __init__(self, message: str = "Failed to connect to email provider.") -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_type="email-connection-error",
            retryable=True,
        )


class EmailAuthenticationError(EmailProviderError):
    """Raised when SMTP authentication or credentials fail (non-retryable without config change)."""

    def __init__(self, message: str = "SMTP authentication failed.") -> None:
        super().__init__(
            message=message,
            status_code=502,
            error_type="email-auth-error",
            retryable=False,
        )


class EmailConfigurationError(EmailProviderError):
    """Raised when required email settings are missing or invalid."""

    def __init__(self, message: str = "Invalid email provider configuration.") -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_type="email-config-error",
            retryable=False,
        )


class EmailContentError(EmailProviderError):
    """Raised when email content, recipient, or attachments are invalid (non-retryable)."""

    def __init__(self, message: str = "Email content or recipient is invalid.") -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_type="email-content-error",
            retryable=False,
        )

