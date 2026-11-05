"""Unit tests for DiscoveryService business logic and orchestration."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import DomainException, EntityAlreadyExistsError, EntityNotFoundError
from app.modules.discovery.models import (
    DiscoveryRun,
    DiscoveryRunStatusEnum,
    JobSource,
    JobSourceTypeEnum,
)
from app.modules.discovery.schemas import JobSourceCreateRequest, JobSourceUpdateRequest
from app.modules.discovery.service import DiscoveryService


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_source_success(mock_repo: MagicMock, mock_session: AsyncMock) -> None:
    service = DiscoveryService(repository=mock_repo)
    now = datetime.now(UTC)

    mock_repo.get_source_by_name = AsyncMock(return_value=None)
    created_source = JobSource(
        id=uuid.uuid4(),
        name="Stripe Greenhouse",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        is_enabled=True,
        polling_interval_minutes=360,
        configuration={"board_token": "stripe"},
        created_at=now,
        updated_at=now,
    )
    mock_repo.create_source = AsyncMock(return_value=created_source)

    request = JobSourceCreateRequest(
        name="Stripe Greenhouse",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        configuration={"board_token": "stripe"},
    )

    response = await service.create_source(mock_session, request)

    assert response.name == "Stripe Greenhouse"
    assert response.source_type == JobSourceTypeEnum.GREENHOUSE
    mock_repo.create_source.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_source_duplicate_name_conflict(
    mock_repo: MagicMock, mock_session: AsyncMock
) -> None:
    service = DiscoveryService(repository=mock_repo)

    existing = JobSource(
        id=uuid.uuid4(),
        name="Existing Source",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        configuration={"board_token": "existing"},
    )
    mock_repo.get_source_by_name = AsyncMock(return_value=existing)

    request = JobSourceCreateRequest(
        name="Existing Source",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        configuration={"board_token": "newtoken"},
    )

    with pytest.raises(EntityAlreadyExistsError):
        await service.create_source(mock_session, request)


@pytest.mark.asyncio
async def test_get_source_not_found(mock_repo: MagicMock, mock_session: AsyncMock) -> None:
    service = DiscoveryService(repository=mock_repo)
    mock_repo.get_source_by_id = AsyncMock(return_value=None)

    with pytest.raises(EntityNotFoundError):
        await service.get_source(mock_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_update_source_success(mock_repo: MagicMock, mock_session: AsyncMock) -> None:
    service = DiscoveryService(repository=mock_repo)
    source_id = uuid.uuid4()
    now = datetime.now(UTC)

    source = JobSource(
        id=source_id,
        name="Old Name",
        source_type=JobSourceTypeEnum.LEVER,
        base_url="https://api.lever.co",
        is_enabled=True,
        polling_interval_minutes=360,
        configuration={"company_id": "oldcomp"},
        created_at=now,
        updated_at=now,
    )
    mock_repo.get_source_by_id = AsyncMock(return_value=source)
    mock_repo.get_source_by_name = AsyncMock(return_value=None)
    mock_repo.get_latest_run_for_source = AsyncMock(return_value=None)

    updated_source = JobSource(
        id=source_id,
        name="New Name",
        source_type=JobSourceTypeEnum.LEVER,
        base_url="https://api.lever.co",
        is_enabled=False,
        polling_interval_minutes=180,
        configuration={"company_id": "newcomp"},
        created_at=now,
        updated_at=now,
    )
    mock_repo.update_source = AsyncMock(return_value=updated_source)

    request = JobSourceUpdateRequest(
        name="New Name",
        is_enabled=False,
        polling_interval_minutes=180,
        configuration={"company_id": "newcomp"},
    )

    resp = await service.update_source(mock_session, source_id, request)
    assert resp.name == "New Name"
    assert resp.is_enabled is False
    assert resp.polling_interval_minutes == 180


@pytest.mark.asyncio
async def test_trigger_discovery_disabled_source_raises_error(
    mock_repo: MagicMock, mock_session: AsyncMock
) -> None:
    service = DiscoveryService(repository=mock_repo)
    source_id = uuid.uuid4()

    source = JobSource(
        id=source_id,
        name="Disabled Source",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        is_enabled=False,
        configuration={"board_token": "disabled"},
    )
    mock_repo.get_source_by_id = AsyncMock(return_value=source)

    with pytest.raises(DomainException, match="currently disabled"):
        await service.trigger_discovery_for_source(mock_session, source_id)


@pytest.mark.asyncio
async def test_trigger_discovery_success_dispatches_task(
    mock_repo: MagicMock, mock_session: AsyncMock
) -> None:
    service = DiscoveryService(repository=mock_repo)
    source_id = uuid.uuid4()
    now = datetime.now(UTC)

    source = JobSource(
        id=source_id,
        name="Active Source",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        is_enabled=True,
        configuration={"board_token": "active"},
        created_at=now,
        updated_at=now,
    )
    mock_repo.get_source_by_id = AsyncMock(return_value=source)

    run = DiscoveryRun(
        id=uuid.uuid4(),
        job_source_id=source_id,
        started_at=now,
        status=DiscoveryRunStatusEnum.PENDING,
        jobs_discovered=0,
        jobs_created=0,
        jobs_updated=0,
        created_at=now,
    )
    mock_repo.create_discovery_run = AsyncMock(return_value=run)

    with patch("app.modules.discovery.service.discover_source_jobs_task.delay") as mock_delay:
        resp = await service.trigger_discovery_for_source(mock_session, source_id)
        assert resp.id == run.id
        assert resp.status == DiscoveryRunStatusEnum.PENDING
        mock_delay.assert_called_once_with(str(source_id))
