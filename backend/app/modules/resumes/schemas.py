"""Pydantic schemas and upload validation utilities for Resume Management."""

import io
import uuid
import zipfile
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

MAX_RESUME_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx"}

T = TypeVar("T")


class PaginationMetadata(BaseModel):
    """Standard pagination envelope metadata."""

    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total count of matching items")
    total_pages: int = Field(ge=0, description="Total pages available")
    has_next: bool = Field(description="Whether a next page exists")
    has_prev: bool = Field(description="Whether a previous page exists")


class PaginatedResponse[T](BaseModel):
    """Generic envelope for paginated resource collections."""

    items: list[T]
    pagination: PaginationMetadata


class ResumeVersionSummary(BaseModel):
    """Compact summary of a parsed resume version."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    is_valid: bool
    processing_status: str
    created_at: datetime


class ResumeVersionResponse(BaseModel):
    """Full detail of a parsed resume version including structured sections."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    master_resume_id: uuid.UUID
    version_number: int
    structured_content: dict[str, Any]
    template_metadata: dict[str, Any] | None = None
    checksum_sha256: str
    is_valid: bool
    processing_status: str
    parsing_error: str | None = None
    created_at: datetime


class MasterResumeSummary(BaseModel):
    """Public summary of an uploaded master resume."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    latest_version: ResumeVersionSummary | None = None


class MasterResumeDetailResponse(BaseModel):
    """Detailed response for a master resume with active version and version history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    original_filename: str
    storage_key: str
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    active_version: ResumeVersionResponse | None = None
    versions: list[ResumeVersionSummary] = []


def validate_resume_file(filename: str, content: bytes, content_type: str | None = None) -> str:
    """Validate resume file upload size, extension, and binary magic bytes.

    Returns:
        The validated canonical MIME type string.

    Raises:
        ValueError: If the file is empty, too large, invalid extension, or fails magic bytes check.
    """
    if not filename or not filename.strip():
        raise ValueError("Uploaded file must have a valid filename.")

    clean_name = filename.strip()
    ext = ("." + clean_name.rsplit(".", 1)[-1].lower()) if "." in clean_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '{ext}'. Only .pdf and .docx are supported.")

    if content_type and content_type.lower().strip() not in (
        ALLOWED_MIME_TYPES | {"application/octet-stream", "binary/octet-stream"}
    ):
        raise ValueError(f"Unsupported Content-Type header: '{content_type}'.")

    file_size = len(content)
    if file_size == 0:
        raise ValueError("Uploaded file is empty (0 bytes).")

    if file_size > MAX_RESUME_FILE_SIZE_BYTES:
        max_mb = MAX_RESUME_FILE_SIZE_BYTES // (1024 * 1024)
        raise ValueError(f"Uploaded file exceeds maximum allowed size of {max_mb}MB.")

    # Validate Magic Bytes / File Signatures
    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF file signature. File header does not match PDF standard.")
        return "application/pdf"

    if ext == ".docx":
        # DOCX files are zip archives starting with PK\x03\x04
        if not content.startswith(b"PK\x03\x04"):
            raise ValueError(
                "Invalid DOCX file signature. File header does not match OpenXML standard."
            )
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Check for standard Word document entry
                namelist = zf.namelist()
                if "word/document.xml" not in namelist:
                    raise ValueError(
                        "Corrupted DOCX archive: missing internal 'word/document.xml'."
                    )
        except zipfile.BadZipFile as exc:
            raise ValueError(f"Invalid DOCX archive structure: {exc}") from exc

        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    raise ValueError(f"Unsupported file format: {ext}")
