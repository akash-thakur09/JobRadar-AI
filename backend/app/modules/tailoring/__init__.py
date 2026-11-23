"""Resume Tailoring domain module."""

from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum
from app.modules.tailoring.evidence import CandidateEvidenceVault
from app.modules.tailoring.exceptions import (
    ClaimValidationError,
    EvidenceNotFoundError,
    InvalidStateTransitionError,
    RenderingError,
    TailoringError,
)
from app.modules.tailoring.models import TailoredResume
from app.modules.tailoring.renderer import ResumeRenderer
from app.modules.tailoring.repository import TailoringRepository
from app.modules.tailoring.schemas import (
    ClaimValidationReport,
    TailoredEducationItem,
    TailoredExperienceItem,
    TailoredProjectItem,
    TailoredResumeContent,
    TailoredResumeDetailResponse,
    TailoredResumeSummaryResponse,
    TailorResumeRequest,
)
from app.modules.tailoring.service import TailoringService, get_tailoring_service

__all__ = [
    "CandidateEvidenceVault",
    "ClaimValidationError",
    "ClaimValidationReport",
    "EvidenceNotFoundError",
    "InvalidStateTransitionError",
    "RenderingError",
    "RenderingStrategyEnum",
    "ResumeRenderer",
    "TailoredEducationItem",
    "TailoredExperienceItem",
    "TailoredProjectItem",
    "TailoredResume",
    "TailoredResumeContent",
    "TailoredResumeDetailResponse",
    "TailoredResumeStatusEnum",
    "TailoredResumeSummaryResponse",
    "TailoringError",
    "TailoringRepository",
    "TailoringService",
    "TailorResumeRequest",
    "get_tailoring_service",
]
