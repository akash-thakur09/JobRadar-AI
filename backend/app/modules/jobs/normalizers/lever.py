"""Lever ATS payload normalizer."""

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
    if source.configuration:
        config_name = source.configuration.get("company_name")
        if config_name and isinstance(config_name, str) and config_name.strip():
            return config_name.strip()
        company_id = source.configuration.get("company_id") or source.configuration.get("site")
        if company_id and isinstance(company_id, str) and company_id.strip():
            # If name is just the slug, title-casing it is cleaner than raw slug
            candidate = company_id.strip().replace("-", " ").replace("_", " ").title()
            if candidate:
                pass  # Fall through to name check below if source.name is descriptive

    name = source.name
    # Strip common platform suffixes (e.g. "Stripe Lever" -> "Stripe")
    for suffix in ("Lever", "lever", "Job Board", "Jobs"):
        name = name.replace(suffix, "").strip()
    return name.strip() or "Unknown Company"


def _extract_workplace_type(
    payload: dict[str, Any], location_str: str, title: str
) -> WorkplaceTypeEnum:
    """Determine workplace arrangement from Lever workplaceType field, location, or title."""
    wp_field = str(payload.get("workplaceType", "")).lower().strip()
    if wp_field == "remote" or "remote" in wp_field:
        return WorkplaceTypeEnum.REMOTE
    if wp_field == "hybrid" or "hybrid" in wp_field:
        return WorkplaceTypeEnum.HYBRID
    if wp_field in ("onsite", "on-site"):
        return WorkplaceTypeEnum.ONSITE

    combined = f"{location_str} {title}".lower()
    if "hybrid" in combined:
        return WorkplaceTypeEnum.HYBRID
    if "remote" in combined or "anywhere" in combined or "distributed" in combined:
        return WorkplaceTypeEnum.REMOTE
    if "onsite" in combined or "on-site" in combined or "in-office" in combined:
        return WorkplaceTypeEnum.ONSITE

    return WorkplaceTypeEnum.UNKNOWN


def _extract_employment_type(categories: dict[str, Any], title: str) -> EmploymentTypeEnum:
    """Determine employment classification from Lever commitment category or title."""
    commitment = str(categories.get("commitment", "")).lower().strip()
    combined = f"{commitment} {title.lower()}"

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


def _parse_lever_created_at(val: Any) -> datetime | None:
    """Parse Lever createdAt which is typically an epoch timestamp in milliseconds or ISO string."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        # Lever timestamps are in milliseconds (e.g. 1600000000000)
        ts = float(val)
        if ts > 1e11:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=UTC)
        except (ValueError, OSError):
            return None
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        # Check if numeric string
        try:
            ts = float(val_str)
            if ts > 1e11:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=UTC)
        except (ValueError, OSError):
            pass
        # Try ISO string format
        try:
            clean_str = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return None
    return None


class LeverNormalizer(BaseJobNormalizer):
    """Normalizes raw Lever job payloads into canonical DTO representation."""

    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.LEVER

    def normalize(self, record: JobSourceRecord, source: JobSource) -> NormalizedJobDTO:
        payload = record.raw_payload or {}
        warnings: list[str] = []

        # 1. Title
        title = str(payload.get("text", "")).strip()
        if not title:
            title = "Untitled Position"
            warnings.append(
                "Missing 'text' (title) in Lever payload; defaulted to 'Untitled Position'."
            )

        # 2. Company Name
        company_name = _derive_company_name(source)

        # 3. Location
        categories = (
            payload.get("categories", {}) if isinstance(payload.get("categories"), dict) else {}
        )
        loc_val = categories.get("location") or payload.get("country")
        cleaned_location = " ".join(str(loc_val).split()) if loc_val else None

        # 4. Description Content
        description_parts: list[str] = []
        raw_desc = payload.get("description") or payload.get("descriptionPlain") or ""
        if raw_desc:
            description_parts.append(str(raw_desc))

        lists = payload.get("lists", [])
        if isinstance(lists, list):
            for lst in lists:
                if isinstance(lst, dict):
                    hdr = lst.get("text", "")
                    content = lst.get("content", "")
                    if hdr or content:
                        description_parts.append(f"<h3>{hdr}</h3>\n{content}")

        additional = payload.get("additional") or payload.get("additionalPlain") or ""
        if additional:
            description_parts.append(str(additional))

        combined_html = "\n\n".join(description_parts)
        description_text = clean_html_description(combined_html)
        if not description_text:
            warnings.append("Empty job description content in Lever payload.")

        # 5. Workplace Type
        workplace_type = _extract_workplace_type(
            payload=payload,
            location_str=cleaned_location or "",
            title=title,
        )

        # 6. Employment Type
        employment_type = _extract_employment_type(categories, title)

        # 7. Application URL
        raw_url = payload.get("hostedUrl") or payload.get("applyUrl") or record.source_job_url
        application_url = sanitize_application_url(str(raw_url))

        # 8. Posting Date
        posted_at = _parse_lever_created_at(payload.get("createdAt") or record.raw_posted_at)

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
                "team": categories.get("team"),
                "department": categories.get("department"),
                "commitment": categories.get("commitment"),
                "workplaceType": payload.get("workplaceType"),
            },
            normalization_warnings=warnings,
        )
