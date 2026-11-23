"""Convert public career-page listings to canonical job data."""

from datetime import UTC, datetime
from typing import Any

from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.jobs.deduplicator import clean_html_description, sanitize_application_url
from app.modules.jobs.models import JobSourceRecord
from app.modules.jobs.normalizers.base import BaseJobNormalizer
from app.modules.jobs.schemas import NormalizedJobDTO

EMPLOYMENT_TYPES = {
    "FULL_TIME": EmploymentTypeEnum.FULL_TIME,
    "PART_TIME": EmploymentTypeEnum.PART_TIME,
    "CONTRACT": EmploymentTypeEnum.CONTRACT,
    "CONTRACTOR": EmploymentTypeEnum.CONTRACT,
    "INTERN": EmploymentTypeEnum.INTERNSHIP,
    "INTERNSHIP": EmploymentTypeEnum.INTERNSHIP,
    "TEMPORARY": EmploymentTypeEnum.TEMPORARY,
    "SEASONAL": EmploymentTypeEnum.TEMPORARY,
}


def _property(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else None


def _clean_text(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _location(value: Any) -> str:
    places = value if isinstance(value, list) else [value]
    locations: list[str] = []
    for place in places:
        address = _property(place, "address")
        if isinstance(address, dict):
            country = address.get("addressCountry")
            fields = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                _property(country, "name") if isinstance(country, dict) else country,
            ]
            location = ", ".join(filter(None, map(_clean_text, fields)))
        else:
            location = _clean_text(address or _property(place, "name") or place)
        if location and location not in locations:
            locations.append(location)
    return "; ".join(locations)


def _posted_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        posted = datetime.fromisoformat(value)
    except ValueError:
        return None
    return posted if posted.tzinfo is not None else posted.replace(tzinfo=UTC)


class CareerPageNormalizer(BaseJobNormalizer):
    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.CAREER_PAGE

    def normalize(self, record: JobSourceRecord, source: JobSource) -> NormalizedJobDTO:
        payload = record.raw_payload
        company = _clean_text(source.configuration.get("company_name")) or _clean_text(
            _property(payload.get("hiringOrganization"), "name")
        )
        location = _location(payload.get("jobLocation"))
        arrangement = _clean_text(payload.get("jobLocationType")).upper()
        workplace = {
            "TELECOMMUTE": WorkplaceTypeEnum.REMOTE,
            "REMOTE": WorkplaceTypeEnum.REMOTE,
            "HYBRID": WorkplaceTypeEnum.HYBRID,
            "ONSITE": WorkplaceTypeEnum.ONSITE,
        }.get(arrangement, WorkplaceTypeEnum.UNKNOWN)
        employment = payload.get("employmentType")
        employment_types = employment if isinstance(employment, list) else [employment]
        types = {
            EMPLOYMENT_TYPES[code]
            for value in employment_types
            if (code := _clean_text(value).upper().replace("-", "_").replace(" ", "_"))
            in EMPLOYMENT_TYPES
        }
        description = payload.get("description")
        text = clean_html_description(description) if isinstance(description, str) else ""
        return NormalizedJobDTO(
            source_record_id=record.id,
            job_source_id=record.job_source_id,
            external_job_id=record.external_job_id,
            company_name=(company or source.name)[:150],
            title=(_clean_text(payload.get("title")) or "Untitled position")[:200],
            description_text=text,
            application_url=sanitize_application_url(record.source_job_url, preserve_path=True),
            normalized_location=location[:150] or None,
            workplace_type=workplace,
            employment_type=next(iter(types)) if len(types) == 1 else EmploymentTypeEnum.UNKNOWN,
            posted_at=_posted_at(record.raw_posted_at),
            normalization_warnings=[] if text else ["Career page did not provide a description."],
        )
