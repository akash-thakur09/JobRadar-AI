"""Master API router aggregating version 1 routes."""

from fastapi import APIRouter

from app.api.routes.candidate import router as candidate_router
from app.api.routes.discovery import discovery_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import jobs_router
from app.api.routes.matches import matches_router
from app.api.routes.resumes import router as resumes_router

api_v1_router = APIRouter()

# Register core monitoring routes
api_v1_router.include_router(health_router)

# Register candidate profile and preferences routes
api_v1_router.include_router(candidate_router)

# Register master resume management routes
api_v1_router.include_router(resumes_router)

# Register job discovery engine routes
api_v1_router.include_router(discovery_router)

# Register canonical jobs and normalization routes
api_v1_router.include_router(jobs_router)

# Register candidate matching and scoring routes
api_v1_router.include_router(matches_router)
