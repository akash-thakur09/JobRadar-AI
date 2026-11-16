"""Unit tests for Pipeline Orchestration REST API routes."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.database.session import get_db_session
from app.main import create_app
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.exceptions import (
    ActivePipelineRunConflictError,
    InvalidPipelineRunStateTransitionError,
    PipelineError,
    PipelineRunNotFoundError,
)
from app.modules.pipeline.models import PipelineRun
from app.modules.pipeline.schemas import (
    PipelineRunListResponse,
    PipelineRunMetrics,
    PipelineRunRead,
    PipelineRunSummary,
)
from app.modules.pipeline.service import get_pipeline_service
from app.modules.resumes.schemas import PaginationMetadata


@pytest.fixture
def mock_pipeline_service() -> MagicMock:
    """Fixture providing mock PipelineOrchestrationService."""
    return MagicMock()


@pytest.fixture
def client(mock_pipeline_service: MagicMock) -> httpx.AsyncClient:
    """Async test client with dependency overrides."""
    app = create_app()
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
async def test_start_pipeline_run_endpoint_success(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """POST /api/v1/pipeline-runs returns 202 Accepted with PENDING run."""
    run_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_run = PipelineRun(
        id=run_id,
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.PENDING,
        trigger_type=PipelineTriggerTypeEnum.MANUAL,
    )
    mock_pipeline_service.start_pipeline_run = AsyncMock(return_value=mock_run)

    mock_read = PipelineRunRead(
        id=run_id,
        candidate_profile_id=candidate_id,
        trigger_type=PipelineTriggerTypeEnum.MANUAL,
        status=PipelineRunStatusEnum.PENDING,
        created_at=now,
        updated_at=now,
        metrics=PipelineRunMetrics(),
    )
    mock_pipeline_service.get_pipeline_run = AsyncMock(return_value=mock_read)

    response = await client.post(
        "/api/v1/pipeline-runs",
        json={"candidate_profile_id": str(candidate_id), "trigger_type": "MANUAL"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["id"] == str(run_id)
    assert data["status"] == "PENDING"
    assert data["trigger_type"] == "MANUAL"


@pytest.mark.unit
async def test_start_pipeline_run_endpoint_candidate_not_found(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """POST /api/v1/pipeline-runs returns 404 when candidate is missing."""
    cand_id = uuid.uuid4()
    mock_pipeline_service.start_pipeline_run = AsyncMock(
        side_effect=PipelineError(
            f"Candidate profile '{cand_id}' does not exist.",
            status_code=404,
            error_type="candidate-profile-not-found",
        )
    )

    response = await client.post(
        "/api/v1/pipeline-runs",
        json={"candidate_profile_id": str(cand_id)},
    )

    assert response.status_code == 404
    data = response.json()
    assert "does not exist" in data["detail"]


@pytest.mark.unit
async def test_start_pipeline_run_endpoint_active_conflict(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """POST /api/v1/pipeline-runs returns 409 Conflict when candidate already has active run."""
    cand_id = uuid.uuid4()
    mock_pipeline_service.start_pipeline_run = AsyncMock(
        side_effect=ActivePipelineRunConflictError(candidate_profile_id=cand_id)
    )

    response = await client.post(
        "/api/v1/pipeline-runs",
        json={"candidate_profile_id": str(cand_id)},
    )

    assert response.status_code == 409
    data = response.json()
    assert "already running" in data["detail"]


@pytest.mark.unit
async def test_list_pipeline_runs_endpoint(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """GET /api/v1/pipeline-runs returns 200 OK with paginated list."""
    run_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    now = datetime.now(UTC)

    summary = PipelineRunSummary(
        id=run_id,
        candidate_profile_id=candidate_id,
        trigger_type=PipelineTriggerTypeEnum.MANUAL,
        status=PipelineRunStatusEnum.COMPLETED,
        created_at=now,
        updated_at=now,
        jobs_discovered=12,
        matches_qualified=4,
        resumes_generated=4,
        notifications_sent=4,
    )
    pagination = PaginationMetadata(
        page=1,
        page_size=20,
        total_items=1,
        total_pages=1,
        has_next=False,
        has_prev=False,
    )

    mock_pipeline_service.list_pipeline_runs = AsyncMock(
        return_value=PipelineRunListResponse(items=[summary], pagination=pagination)
    )

    response = await client.get("/api/v1/pipeline-runs")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(run_id)
    assert data["items"][0]["jobs_discovered"] == 12


@pytest.mark.unit
async def test_get_pipeline_run_endpoint_success(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """GET /api/v1/pipeline-runs/{id} returns 200 OK with detail metrics."""
    run_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    now = datetime.now(UTC)

    read_model = PipelineRunRead(
        id=run_id,
        candidate_profile_id=candidate_id,
        trigger_type=PipelineTriggerTypeEnum.MANUAL,
        status=PipelineRunStatusEnum.COMPLETED,
        created_at=now,
        updated_at=now,
        metrics=PipelineRunMetrics(jobs_discovered=5, matches_qualified=2),
    )
    mock_pipeline_service.get_pipeline_run = AsyncMock(return_value=read_model)

    response = await client.get(f"/api/v1/pipeline-runs/{run_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(run_id)
    assert data["metrics"]["jobs_discovered"] == 5


@pytest.mark.unit
async def test_get_pipeline_run_endpoint_not_found(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """GET /api/v1/pipeline-runs/{id} returns 404 when not found."""
    run_id = uuid.uuid4()
    mock_pipeline_service.get_pipeline_run = AsyncMock(side_effect=PipelineRunNotFoundError(run_id))

    response = await client.get(f"/api/v1/pipeline-runs/{run_id}")

    assert response.status_code == 404
    data = response.json()
    assert "was not found" in data["detail"]


@pytest.mark.unit
async def test_cancel_pipeline_run_endpoint_success(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """POST /api/v1/pipeline-runs/{id}/cancel returns 200 OK on cancellation."""
    run_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    cancelled_run = PipelineRun(
        id=run_id,
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.CANCELLED,
    )
    mock_pipeline_service.cancel_pipeline_run = AsyncMock(return_value=cancelled_run)

    response = await client.post(f"/api/v1/pipeline-runs/{run_id}/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_run_id"] == str(run_id)
    assert data["status"] == "CANCELLED"


@pytest.mark.unit
async def test_cancel_pipeline_run_endpoint_conflict(
    client: httpx.AsyncClient, mock_pipeline_service: MagicMock
) -> None:
    """POST /api/v1/pipeline-runs/{id}/cancel returns 409 Conflict if already terminal."""
    run_id = uuid.uuid4()
    mock_pipeline_service.cancel_pipeline_run = AsyncMock(
        side_effect=InvalidPipelineRunStateTransitionError("COMPLETED", "CANCELLED")
    )

    response = await client.post(f"/api/v1/pipeline-runs/{run_id}/cancel")

    assert response.status_code == 409
    data = response.json()
    assert "Cannot transition pipeline run" in data["detail"]
