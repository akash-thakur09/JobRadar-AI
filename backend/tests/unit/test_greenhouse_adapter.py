"""Unit tests for Greenhouse Job Source Adapter."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.modules.discovery.adapters.greenhouse import GreenhouseAdapter
from app.modules.discovery.exceptions import (
    InvalidSourceConfigError,
    MalformedPayloadError,
    NetworkTimeoutError,
    RateLimitExceededError,
    SourceNotFoundError,
    UpstreamServerError,
)
from app.modules.discovery.models import JobSourceTypeEnum

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def greenhouse_sample_payload() -> dict:
    with open(FIXTURES_DIR / "greenhouse_sample.json", encoding="utf-8") as f:
        return json.load(f)


def test_greenhouse_adapter_source_type() -> None:
    adapter = GreenhouseAdapter()
    assert adapter.source_type == JobSourceTypeEnum.GREENHOUSE


def test_greenhouse_validate_configuration_valid() -> None:
    adapter = GreenhouseAdapter()
    adapter.validate_configuration({"board_token": "stripe"})
    adapter.validate_configuration({"board_token": "airbnb-inc_123"})


def test_greenhouse_validate_configuration_missing_or_invalid() -> None:
    adapter = GreenhouseAdapter()
    with pytest.raises(InvalidSourceConfigError, match="must include a non-empty 'board_token'"):
        adapter.validate_configuration({})

    with pytest.raises(InvalidSourceConfigError, match="must include a non-empty 'board_token'"):
        adapter.validate_configuration({"board_token": "   "})

    with pytest.raises(InvalidSourceConfigError, match="Invalid Greenhouse board_token"):
        adapter.validate_configuration({"board_token": "bad token!@#$"})


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_success(greenhouse_sample_payload: dict) -> None:
    adapter = GreenhouseAdapter()
    board_token = "acme"

    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get(f"/v1/boards/{board_token}/jobs?content=true").mock(
            return_value=httpx.Response(200, json=greenhouse_sample_payload)
        )

        async with httpx.AsyncClient() as client:
            result = await adapter.discover_jobs(
                base_url="https://boards-api.greenhouse.io",
                configuration={"board_token": board_token},
                client=client,
            )

    assert result.source_identifier == "acme"
    assert result.source_type == JobSourceTypeEnum.GREENHOUSE
    assert len(result.jobs) == 2

    job1 = result.jobs[0]
    assert job1.external_id == "4123456"
    assert job1.source_url == "https://boards.greenhouse.io/acme/jobs/4123456"
    assert "Senior Distributed Systems Engineer" in job1.raw_payload["title"]
    assert job1.raw_posted_at == "2026-11-01T14:30:00Z"

    job2 = result.jobs[1]
    assert job2.external_id == "4123457"
    assert job2.source_url == "https://boards.greenhouse.io/acme/jobs/4123457"


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_empty_board() -> None:
    adapter = GreenhouseAdapter()
    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get("/v1/boards/empty/jobs?content=true").mock(
            return_value=httpx.Response(200, json={"jobs": []})
        )

        async with httpx.AsyncClient() as client:
            result = await adapter.discover_jobs(
                base_url="https://boards-api.greenhouse.io",
                configuration={"board_token": "empty"},
                client=client,
            )

    assert result.jobs == []
    assert result.warnings == []


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_not_found_404() -> None:
    adapter = GreenhouseAdapter()
    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get("/v1/boards/nonexistent/jobs?content=true").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(SourceNotFoundError, match="nonexistent"):
                await adapter.discover_jobs(
                    base_url="https://boards-api.greenhouse.io",
                    configuration={"board_token": "nonexistent"},
                    client=client,
                )


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_rate_limited_429() -> None:
    adapter = GreenhouseAdapter()
    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get("/v1/boards/ratelimited/jobs?content=true").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "60"},
                text="Too Many Requests",
            )
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.discover_jobs(
                    base_url="https://boards-api.greenhouse.io",
                    configuration={"board_token": "ratelimited"},
                    client=client,
                )
            assert exc_info.value.retry_after == 60


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_upstream_500() -> None:
    adapter = GreenhouseAdapter()
    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get("/v1/boards/servererror/jobs?content=true").mock(
            return_value=httpx.Response(502, text="Bad Gateway")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(UpstreamServerError):
                await adapter.discover_jobs(
                    base_url="https://boards-api.greenhouse.io",
                    configuration={"board_token": "servererror"},
                    client=client,
                )


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_timeout() -> None:
    adapter = GreenhouseAdapter()
    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get("/v1/boards/timeout/jobs?content=true").mock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(NetworkTimeoutError):
                await adapter.discover_jobs(
                    base_url="https://boards-api.greenhouse.io",
                    configuration={"board_token": "timeout"},
                    client=client,
                )


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_malformed_json() -> None:
    adapter = GreenhouseAdapter()
    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get("/v1/boards/malformed/jobs?content=true").mock(
            return_value=httpx.Response(200, text="not valid json")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(MalformedPayloadError, match="Failed to decode response as JSON"):
                await adapter.discover_jobs(
                    base_url="https://boards-api.greenhouse.io",
                    configuration={"board_token": "malformed"},
                    client=client,
                )


@pytest.mark.asyncio
async def test_greenhouse_discover_jobs_missing_jobs_key() -> None:
    adapter = GreenhouseAdapter()
    with respx.mock(base_url="https://boards-api.greenhouse.io") as respx_mock:
        respx_mock.get("/v1/boards/badstructure/jobs?content=true").mock(
            return_value=httpx.Response(200, json={"wrong_key": []})
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(
                MalformedPayloadError, match="missing the expected root 'jobs' list"
            ):
                await adapter.discover_jobs(
                    base_url="https://boards-api.greenhouse.io",
                    configuration={"board_token": "badstructure"},
                    client=client,
                )
