"""Unit tests for Lever Job Source Adapter."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.modules.discovery.adapters.lever import LeverAdapter
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
def lever_sample_payload() -> list:
    with open(FIXTURES_DIR / "lever_sample.json", encoding="utf-8") as f:
        return json.load(f)


def test_lever_adapter_source_type() -> None:
    adapter = LeverAdapter()
    assert adapter.source_type == JobSourceTypeEnum.LEVER


def test_lever_validate_configuration_valid() -> None:
    adapter = LeverAdapter()
    adapter.validate_configuration({"company_id": "netflix"})
    adapter.validate_configuration({"site": "lever-demo"})


def test_lever_validate_configuration_missing_or_invalid() -> None:
    adapter = LeverAdapter()
    with pytest.raises(
        InvalidSourceConfigError, match="must include a non-empty 'company_id' or 'site'"
    ):
        adapter.validate_configuration({})

    with pytest.raises(
        InvalidSourceConfigError, match="must include a non-empty 'company_id' or 'site'"
    ):
        adapter.validate_configuration({"company_id": "   "})

    with pytest.raises(InvalidSourceConfigError, match="Invalid Lever company identifier"):
        adapter.validate_configuration({"company_id": "invalid identifier with spaces!"})


@pytest.mark.asyncio
async def test_lever_discover_jobs_success(lever_sample_payload: list) -> None:
    adapter = LeverAdapter()
    company_id = "acme-corp"

    with respx.mock(base_url="https://api.lever.co") as respx_mock:
        respx_mock.get(f"/v0/postings/{company_id}?mode=json").mock(
            return_value=httpx.Response(200, json=lever_sample_payload)
        )

        async with httpx.AsyncClient() as client:
            result = await adapter.discover_jobs(
                base_url="https://api.lever.co",
                configuration={"company_id": company_id},
                client=client,
            )

    assert result.source_identifier == "acme-corp"
    assert result.source_type == JobSourceTypeEnum.LEVER
    assert len(result.jobs) == 2

    job1 = result.jobs[0]
    assert job1.external_id == "e4b5f8c2-3e2a-4b91-9c8a-1234567890ab"
    assert "https://jobs.lever.co/acme-corp/e4b5f8c2-3e2a-4b91-9c8a-1234567890ab" in job1.source_url
    assert job1.raw_payload["text"] == "Principal Backend Architect"
    assert job1.raw_posted_at == "1730467200000"

    job2 = result.jobs[1]
    assert job2.external_id == "f8a1c9e4-1b2c-3d4e-5f6a-7b8c9d0e1f2a"
    assert job2.raw_payload["text"] == "Senior DevOps / SRE Specialist"


@pytest.mark.asyncio
async def test_lever_discover_jobs_empty_postings() -> None:
    adapter = LeverAdapter()
    with respx.mock(base_url="https://api.lever.co") as respx_mock:
        respx_mock.get("/v0/postings/empty?mode=json").mock(
            return_value=httpx.Response(200, json=[])
        )

        async with httpx.AsyncClient() as client:
            result = await adapter.discover_jobs(
                base_url="https://api.lever.co",
                configuration={"company_id": "empty"},
                client=client,
            )

    assert result.jobs == []


@pytest.mark.asyncio
async def test_lever_discover_jobs_not_found_404() -> None:
    adapter = LeverAdapter()
    with respx.mock(base_url="https://api.lever.co") as respx_mock:
        respx_mock.get("/v0/postings/missing?mode=json").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(SourceNotFoundError, match="missing"):
                await adapter.discover_jobs(
                    base_url="https://api.lever.co",
                    configuration={"company_id": "missing"},
                    client=client,
                )


@pytest.mark.asyncio
async def test_lever_discover_jobs_rate_limited_429() -> None:
    adapter = LeverAdapter()
    with respx.mock(base_url="https://api.lever.co") as respx_mock:
        respx_mock.get("/v0/postings/limited?mode=json").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "45"}, text="Rate Limit")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.discover_jobs(
                    base_url="https://api.lever.co",
                    configuration={"company_id": "limited"},
                    client=client,
                )
            assert exc_info.value.retry_after == 45


@pytest.mark.asyncio
async def test_lever_discover_jobs_upstream_500() -> None:
    adapter = LeverAdapter()
    with respx.mock(base_url="https://api.lever.co") as respx_mock:
        respx_mock.get("/v0/postings/servererr?mode=json").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(UpstreamServerError):
                await adapter.discover_jobs(
                    base_url="https://api.lever.co",
                    configuration={"company_id": "servererr"},
                    client=client,
                )


@pytest.mark.asyncio
async def test_lever_discover_jobs_timeout() -> None:
    adapter = LeverAdapter()
    with respx.mock(base_url="https://api.lever.co") as respx_mock:
        respx_mock.get("/v0/postings/timeout?mode=json").mock(
            side_effect=httpx.ConnectTimeout("Connect timeout")
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(NetworkTimeoutError):
                await adapter.discover_jobs(
                    base_url="https://api.lever.co",
                    configuration={"company_id": "timeout"},
                    client=client,
                )


@pytest.mark.asyncio
async def test_lever_discover_jobs_malformed_not_list() -> None:
    adapter = LeverAdapter()
    with respx.mock(base_url="https://api.lever.co") as respx_mock:
        respx_mock.get("/v0/postings/badjson?mode=json").mock(
            return_value=httpx.Response(200, json={"error": "not a list"})
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(MalformedPayloadError, match="not the expected top-level list"):
                await adapter.discover_jobs(
                    base_url="https://api.lever.co",
                    configuration={"company_id": "badjson"},
                    client=client,
                )
