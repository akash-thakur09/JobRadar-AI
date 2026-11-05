"""Greenhouse ATS payload normalizer."""

from datetime import UTC, datetime
from typing import Any

from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.jobs.deduplicator import clean_html_description, sanitize_application_url
from app.modules.jobs.models import JobSourceRecord
from app.modules.jobs.normalizers.base import BaseJobNormalizer
from app.modules.jobs.schemas import NormalizedJobDTO


def _derive_company_name(source: JobSource) -> str:
    """Derive display company name from source configuration or name."""
    config_name = source.configuration.get("company_name") if source.configuration else None
    if config_name and isinstance(config_name, str) and config_name.strip():
        return config_name.strip()

    name = source.name
    # Strip common platform suffixes (e.g. "Stripe Greenhouse" -> "Stripe")
    for suffix in ("Greenhouse", "greenhouse", "Job Board", "Jobs"):
        name = name.replace(suffix, "").strip()
    return name.strip() or "Unknown Company"


def _extract_workplace_type(location_str: str, text: str) -> WorkplaceTypeEnum:
    """Determine workplace arrangement from location and description text."""
    combined = f"{location_str} {text}".lower()
    if "hybrid" in combined:
        return WorkplaceTypeEnum.HYBRID
    if "remote" in combined or "anywhere" in combined or "distributed" in combined:
        return WorkplaceTypeEnum.REMOTE
    if "onsite" in combined or "on-site" in combined or "in-office" in combined:
        return WorkplaceTypeEnum.ONSITE
    return WorkplaceTypeEnum.UNKNOWN


def _extract_employment_type(metadata_list: list[dict[str, Any]], title: str) -> EmploymentTypeEnum:
    """Determine employment classification from Greenhouse metadata or title."""
    candidate_strings = [title.lower()]
    for item in metadata_list:
        if isinstance(item, dict):
            val = str(item.get("value", "")).lower()
            candidate_strings.append(val)

    combined = " ".join(candidate_strings)
    if "full-time" in combined or "full time" in combined or "regular" in combined:
        return EmploymentTypeEnum.FULL_TIME
    if "part-time" in combined or "part time" in combined:
        return EmploymentTypeEnum.PART_TIME
    if "contract" in combined or "contractor" in combined or "freelance" in combined:
        return EmploymentTypeEnum.CONTRACT
    if "intern" in combined or "internship" in combined or "co-op" in combined:
        return EmploymentTypeEnum.INTERNSHIP
    if "temp" in combined or "temporary" in combined:
        return EmploymentTypeEnum.TEMPORARY

    return EmploymentTypeEnum.UNKNOWN


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO 8601 timestamp string into timezone-aware UTC datetime."""
    if not dt_str or not isinstance(dt_str, str) or not dt_str.strip():
        return None
    try:
        # Replace Z with UTC offset for fromisoformat compatibility
        clean_str = dt_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


class GreenhouseNormalizer(BaseJobNormalizer):
    """Normalizes raw Greenhouse job payloads into canonical DTO representation."""

    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.GREENHOUSE

    def normalize(self, record: JobSourceRecord, source: JobSource) -> NormalizedJobDTO:
        payload = record.raw_payload or {}
        warnings: list[str] = []

        # 1. Title
        title = str(payload.get("title", "")).strip()
        if not title:
            title = "Untitled Position"
            warnings.append(
                "Missing 'title' in Greenhouse payload; defaulted to 'Untitled Position'."
            )

        # 2. Company Name
        company_name = _derive_company_name(source)

        # 3. Location
        loc_obj = payload.get("location")
        location_name = None
        if isinstance(loc_obj, dict):
            location_name = loc_obj.get("name")
        elif isinstance(loc_obj, str):
            location_name = loc_obj

        if not location_name:
            offices = payload.get("offices", [])
            if offices and isinstance(offices, list) and isinstance(offices[0], dict):
                location_name = offices[0].get("name")

        cleaned_location = " ".join(str(location_name).split()) if location_name else None

        # 4. Description
        raw_html = payload.get("content", "")
        description_text = clean_html_description(str(raw_html))
        if not description_text:
            warnings.append("Empty job description content in Greenhouse payload.")

        # 5. Workplace Type
        workplace_type = _extract_workplace_type(
            location_str=cleaned_location or "",
            text=title,
        )

        # 6. Employment Type
        metadata_list = (
            payload.get("metadata", []) if isinstance(payload.get("metadata"), list) else []
        )
        employment_type = _extract_employment_type(metadata_list, title)

        # 7. Application URL
        raw_url = payload.get("absolute_url") or record.source_job_url
        application_url = sanitize_application_url(str(raw_url))

        # 8. Posting Date
        posted_at = _parse_datetime(payload.get("updated_at") or record.raw_posted_at)

        return NormalizedJobDTO(
            source_record_id=record.id,
            job_source_id=record.job_source_id,
            external_job_id=record.external_job_id,
            company_name=company_name,
            title=title,
            description_text=description_text,
            application_url=application_url,
            normalized_location=cleaned_location,
            workplace_type=workplace_type,
            employment_type=employment_type,
            posted_at=posted_at,
            source_metadata={
                "requisition_id": payload.get("requisition_id"),
                "departments": [
                    d.get("name") for d in payload.get("departments", []) if isinstance(d, dict)
                ],
            },
            normalization_warnings=warnings,
        )
