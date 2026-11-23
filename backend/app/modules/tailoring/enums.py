"""Enumerations for Tailored Resume lifecycle and rendering strategies."""

import enum


class RenderingStrategyEnum(enum.StrEnum):
    """Strategy utilized to compile the tailored resume into PDF."""

    PRESERVED = "PRESERVED"
    FALLBACK = "FALLBACK"


class TailoredResumeStatusEnum(enum.StrEnum):
    """Explicit lifecycle states for job-specific resume tailoring."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    VALIDATING = "VALIDATING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
