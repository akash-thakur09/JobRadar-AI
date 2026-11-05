"""Enumerations for Notification Delivery lifecycle states and types."""

from enum import StrEnum


class NotificationDeliveryStatusEnum(StrEnum):
    """Lifecycle states for notification delivery."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationTypeEnum(StrEnum):
    """Supported notification delivery message categories."""

    IMMEDIATE_TAILORED_JOB = "IMMEDIATE_TAILORED_JOB"

