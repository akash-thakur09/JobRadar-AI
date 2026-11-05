"""Unit tests for Greenhouse and Lever job normalizers."""

import uuid
from datetime import UTC, datetime

import pytest

from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.jobs.models import JobSourceRecord
from app.modules.jobs.normalizers.base import BaseJobNormalizer
from app.modules.jobs.normalizers.greenhouse import GreenhouseNormalizer
from app.modules.jobs.normalizers.lever import LeverNormalizer
from app.modules.jobs.normalizers.registry import get_normalizer_for_source_type


def _make_dummy_source(
    source_type: JobSourceTypeEnum, name: str, config: dict | None = None
) -> JobSource:
    source = JobSource(
        id=uuid.uuid4(),
        name=name,
        source_type=source_type,
        base_url="https://api.example.com",
        configuration=config or {},
        is_enabled=True,
    )
    return source


def _make_dummy_record(
    source: JobSource, external_id: str, payload: dict, source_url: str = "https://example.com/job"
) -> JobSourceRecord:
    record = JobSourceRecord(
        id=uuid.uuid4(),
        job_source_id=source.id,
        external_job_id=external_id,
        source_job_url=source_url,
        raw_payload=payload,
        payload_hash_sha256="abc123hash",
        processing_status="RAW",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    record.job_source = source
    return record


def test_greenhouse_normalizer_standard_payload() -> None:
    source = _make_dummy_source(
        JobSourceTypeEnum.GREENHOUSE,
        name="Stripe Greenhouse",
        config={"company_name": "Stripe"},
    )
    payload = {
        "id": 12345,
        "title": "Senior Backend Engineer",
        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/12345?gh_jid=12345",
        "location": {"name": "San Francisco, CA (Remote)"},
        "content": "<p>Build global payment APIs.</p><ul><li>Scale services</li></ul>",
        "updated_at": "2026-10-15T12:00:00Z",
        "metadata": [{"name": "Employment Type", "value": "Full-Time"}],
        "departments": [{"name": "Engineering"}],
    }
    record = _make_dummy_record(source, external_id="12345", payload=payload)

    normalizer = GreenhouseNormalizer()
    assert normalizer.source_type == JobSourceTypeEnum.GREENHOUSE

    dto = normalizer.normalize(record, source)
    assert dto.company_name == "Stripe"
    assert dto.title == "Senior Backend Engineer"
    assert dto.normalized_location == "San Francisco, CA (Remote)"
    assert dto.workplace_type == WorkplaceTypeEnum.REMOTE
    assert dto.employment_type == EmploymentTypeEnum.FULL_TIME
    assert "Build global payment APIs." in dto.description_text
    assert "• Scale services" in dto.description_text
    assert dto.application_url == "https://boards.greenhouse.io/stripe/jobs/12345"
    assert dto.posted_at == datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    assert len(dto.normalization_warnings) == 0


def test_greenhouse_normalizer_missing_title_and_description() -> None:
    source = _make_dummy_source(JobSourceTypeEnum.GREENHOUSE, name="Unknown ATS")
    record = _make_dummy_record(source, external_id="empty-1", payload={})

    normalizer = GreenhouseNormalizer()
    dto = normalizer.normalize(record, source)

    assert dto.title == "Untitled Position"
    assert dto.description_text == ""
    assert any("Missing 'title'" in w for w in dto.normalization_warnings)
    assert any("Empty job description" in w for w in dto.normalization_warnings)


def test_lever_normalizer_standard_payload() -> None:
    source = _make_dummy_source(
        JobSourceTypeEnum.LEVER,
        name="Datadog Lever",
        config={"company_name": "Datadog", "company_id": "datadog"},
    )
    payload = {
        "id": "lever-999",
        "text": "Staff Infrastructure Engineer",
        "hostedUrl": "https://jobs.lever.co/datadog/lever-999?lever-origin=applied",
        "workplaceType": "hybrid",
        "categories": {
            "location": "New York, NY",
            "commitment": "Full-time",
            "team": "Core Platform",
        },
        "description": "<p>Lead observability systems architecture.</p>",
        "lists": [
            {
                "text": "Requirements",
                "content": "<li>7+ years experience with distributed systems.</li>",
            }
        ],
        "createdAt": 1760000000000,  # epoch ms
    }
    record = _make_dummy_record(source, external_id="lever-999", payload=payload)

    normalizer = LeverNormalizer()
    assert normalizer.source_type == JobSourceTypeEnum.LEVER

    dto = normalizer.normalize(record, source)
    assert dto.company_name == "Datadog"
    assert dto.title == "Staff Infrastructure Engineer"
    assert dto.normalized_location == "New York, NY"
    assert dto.workplace_type == WorkplaceTypeEnum.HYBRID
    assert dto.employment_type == EmploymentTypeEnum.FULL_TIME
    assert "Lead observability systems architecture." in dto.description_text
    assert "Requirements" in dto.description_text
    assert "• 7+ years experience with distributed systems." in dto.description_text
    assert dto.application_url == "https://jobs.lever.co/datadog/lever-999"
    assert dto.posted_at is not None


def test_lever_normalizer_missing_fields() -> None:
    source = _make_dummy_source(JobSourceTypeEnum.LEVER, name="Acme Jobs")
    record = _make_dummy_record(source, external_id="lev-empty", payload={})

    normalizer = LeverNormalizer()
    dto = normalizer.normalize(record, source)

    assert dto.title == "Untitled Position"
    assert dto.description_text == ""
    assert dto.workplace_type == WorkplaceTypeEnum.UNKNOWN
    assert dto.employment_type == EmploymentTypeEnum.UNKNOWN
    assert dto.posted_at is None
    assert len(dto.normalization_warnings) > 0


def test_normalizer_registry() -> None:
    gh_norm = get_normalizer_for_source_type(JobSourceTypeEnum.GREENHOUSE)
    assert isinstance(gh_norm, BaseJobNormalizer)
    assert gh_norm.source_type == JobSourceTypeEnum.GREENHOUSE

    lev_norm = get_normalizer_for_source_type(JobSourceTypeEnum.LEVER)
    assert isinstance(lev_norm, BaseJobNormalizer)
    assert lev_norm.source_type == JobSourceTypeEnum.LEVER

    with pytest.raises(ValueError, match="No job normalizer registered"):
        get_normalizer_for_source_type(JobSourceTypeEnum.CAREER_PAGE)
