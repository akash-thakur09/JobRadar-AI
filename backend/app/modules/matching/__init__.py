"""Matching module package exporting models, schemas, and service."""

from app.modules.matching.models import EligibilityStatusEnum, JobMatch, SemanticAnalysisStatusEnum
from app.modules.matching.repository import MatchingRepository
from app.modules.matching.schemas import (
    JobMatchDetailResponse,
    JobMatchReevaluateResponse,
    JobMatchSummaryResponse,
)
from app.modules.matching.semantic_service import (
    SemanticAnalysisService,
    get_semantic_service,
)
from app.modules.matching.service import MatchingService, get_matching_service

__all__ = [
    "EligibilityStatusEnum",
    "JobMatch",
    "JobMatchDetailResponse",
    "JobMatchReevaluateResponse",
    "JobMatchSummaryResponse",
    "MatchingRepository",
    "MatchingService",
    "SemanticAnalysisService",
    "SemanticAnalysisStatusEnum",
    "get_matching_service",
    "get_semantic_service",
]
