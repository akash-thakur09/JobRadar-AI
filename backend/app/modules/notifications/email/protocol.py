"""Protocol and data structures for email provider implementations."""

from typing import Protocol

from pydantic import BaseModel, Field


class EmailAttachment(BaseModel):
    """Binary or document attachment for an email message."""

    filename: str = Field(description="Name of the attached file, e.g. resume.pdf")
    content: bytes = Field(description="Raw binary content of the attachment")
    content_type: str = Field(
        default="application/pdf",
        description="MIME content type of the attachment",
    )


class EmailMessage(BaseModel):
    """Self-contained email message ready for dispatch via an EmailProvider."""

    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    html_body: str = Field(description="Formatted HTML email body")
    text_body: str = Field(description="Plain text fallback email body")
    from_email: str | None = Field(default=None, description="Sender email address")
    from_name: str | None = Field(default=None, description="Sender display name")
    attachments: list[EmailAttachment] = Field(
        default_factory=list,
        description="List of attached files",
    )


class EmailDeliveryResult(BaseModel):
    """Result of an email transmission attempt."""

    success: bool = Field(description="Whether the provider accepted the email for delivery")
    provider_message_id: str | None = Field(
        default=None,
        description="Message-ID or transaction identifier assigned by the provider",
    )
    error: str | None = Field(
        default=None,
        description="Error description if the delivery attempt failed",
    )


class EmailProvider(Protocol):
    """Protocol interface defining operations required for email notification delivery."""

    async def send_email(self, message: EmailMessage) -> EmailDeliveryResult:
        """Transmit an email message asynchronously to the destination recipient.

        Args:
            message: Formatted EmailMessage with recipient, content, and attachments.

        Returns:
            EmailDeliveryResult indicating success or failure with message ID or error details.

        Raises:
            EmailTimeoutError: If the connection or transmission times out.
            EmailConnectionError: If network connection to SMTP server fails.
            EmailAuthenticationError: If credentials or authentication handshake fails.
            EmailProviderError: For any other provider-level delivery errors.
        """
        ...

    async def ping(self) -> bool:
        """Verify reachability and readiness of the underlying email provider service."""
        ...

