"""Base parser interfaces, models, and deterministic section extraction heuristics."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PreservationCapability(StrEnum):
    """Capability of preserving the original resume template layout."""

    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class ParsedResumeResult:
    """Normalized structured outcome of parsing a resume binary."""

    raw_text: str
    structured_content: dict[str, Any]
    template_metadata: dict[str, Any]
    preservation_capability: PreservationCapability
    extraction_warnings: list[str] = field(default_factory=list)
    is_valid: bool = True


# Standard section header regex patterns
SECTION_HEADER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "summary",
        re.compile(
            r"^(professional\s+summary|executive\s+summary|summary|profile|about\s+me)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "experience",
        re.compile(
            r"^(work\s+experience|professional\s+experience|experience|employment\s+history|work\s+history)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "skills",
        re.compile(
            r"^(technical\s+skills|skills|core\s+competencies|technologies|tools\s+&\s+technologies)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "education",
        re.compile(
            r"^(education|academic\s+background|degrees|academic\s+history)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "projects",
        re.compile(
            r"^(projects|key\s+projects|personal\s+projects|technical\s+projects)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "certifications",
        re.compile(
            r"^(certifications|licenses|courses\s+&\s+certifications|professional\s+credentials)\b",
            re.IGNORECASE,
        ),
    ),
]


def extract_deterministic_sections(raw_text: str) -> dict[str, Any]:
    """Segment extracted resume text into structured sections using deterministic heuristics.

    Maintains section blocks and lines to support future candidate evidence traceability.
    """
    lines = [line.strip() for line in raw_text.splitlines()]

    # Extract basic contact info via regex
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", raw_text)
    phone_match = re.search(
        r"\(?\+?[0-9]{1,3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}", raw_text
    )
    github_match = re.search(r"(github\.com/[a-zA-Z0-9_-]+)", raw_text, re.IGNORECASE)
    linkedin_match = re.search(r"(linkedin\.com/in/[a-zA-Z0-9_-]+)", raw_text, re.IGNORECASE)

    contact_info = {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "github": github_match.group(0) if github_match else None,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
    }

    sections: dict[str, list[str]] = {
        "summary": [],
        "experience": [],
        "skills": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "other": [],
    }

    current_section = "other"

    for line in lines:
        if not line:
            continue

        # Check if line matches a recognized section header
        matched_section = None
        for sec_name, pattern in SECTION_HEADER_PATTERNS:
            # Header line is usually short (< 40 characters) and matches pattern
            if len(line) < 40 and pattern.match(line):
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(line)

    # Flatten skills into itemized list if commas or bullet points are used
    raw_skills = sections.get("skills", [])
    extracted_skills: list[str] = []
    for skill_line in raw_skills:
        for token in re.split(r"[,•|/·\n]", skill_line):
            cleaned = token.strip()
            if cleaned and len(cleaned) < 50:
                extracted_skills.append(cleaned)

    return {
        "contact": contact_info,
        "summary": "\n".join(sections.get("summary", [])).strip() or None,
        "skills": extracted_skills,
        "experience": sections.get("experience", []),
        "education": sections.get("education", []),
        "projects": sections.get("projects", []),
        "certifications": sections.get("certifications", []),
        "other": sections.get("other", []),
    }


class BaseResumeParser(ABC):
    """Abstract base class for document-specific resume parsers."""

    @abstractmethod
    def supports(self, mime_type: str, filename: str) -> bool:
        """Check whether this parser handles the given file type."""
        ...

    @abstractmethod
    async def parse(self, content_bytes: bytes, filename: str) -> ParsedResumeResult:
        """Extract text, layout metadata, and structured content from document bytes."""
        ...
