"""Regression checks for approved public listings and canonical job data."""

import uuid

import httpx
import pytest

from app.modules.discovery.adapters.career_page import CareerPageAdapter
from app.modules.discovery.exceptions import InvalidSourceConfigError
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.jobs.models import JobSourceRecord
from app.modules.jobs.normalizers.registry import get_normalizer_for_source_type

CAREERS = "https://careers.example.test/openings"
MARKUP = """<script type="application/ld+json">{"@graph":[{
    "@type":"JobPosting","title":"Backend Engineer","url":"/jobs/Backend-42",
    "description":"<p>Build Python services.</p>","datePosted":"2026-11-23",
    "jobLocationType":"TELECOMMUTE","employmentType":"FULL_TIME",
    "hiringOrganization":{"name":"QA Company"}
}]}</script>
<a href="/jobs/Backend-42">Duplicate</a>
<a href="/jobs/Infrastructure-43">Infrastructure Engineer</a>
<a href="//another.example.test/jobs/45">External listing</a>
<a href="/jobs-more/other">Unrelated prefix</a>"""


@pytest.mark.unit
async def test_career_page_approval_extraction_and_normalization(monkeypatch):
    monkeypatch.setenv("CAREER_PAGE_ALLOWED_HOSTS", "careers.example.test")
    adapter = CareerPageAdapter()
    config = {"permitted": True, "job_link_prefix": "/jobs/"}
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(200, text=MARKUP, headers={"Content-Type": "text/html"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        jobs = (await adapter.discover_jobs(CAREERS, config, client)).jobs
        with pytest.raises(InvalidSourceConfigError, match="approved"):
            await adapter.discover_jobs("https://unapproved.example.test", config, client)

    assert requests == [CAREERS]
    assert [job.raw_payload["title"] for job in jobs] == [
        "Backend Engineer",
        "Infrastructure Engineer",
    ]
    source = JobSource(
        name="Source", source_type=JobSourceTypeEnum.CAREER_PAGE, configuration=config
    )
    job = jobs[0]
    record = JobSourceRecord(
        id=uuid.uuid4(),
        job_source_id=uuid.uuid4(),
        external_job_id=job.external_id,
        source_job_url=job.source_url,
        raw_payload=job.raw_payload,
        raw_posted_at=job.raw_posted_at,
    )
    normalized = get_normalizer_for_source_type(source.source_type).normalize(record, source)
    assert normalized.company_name == "QA Company"
    assert normalized.application_url == "https://careers.example.test/jobs/Backend-42"
    assert normalized.description_text == "Build Python services."
    assert (normalized.workplace_type, normalized.employment_type) == ("REMOTE", "FULL_TIME")
