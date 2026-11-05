"""DOCX structural extractor using python-docx."""

import asyncio
import io
import logging

import docx

from app.modules.resumes.parsers.base import (
    BaseResumeParser,
    ParsedResumeResult,
    PreservationCapability,
    extract_deterministic_sections,
)

logger = logging.getLogger(__name__)


class DocxParser(BaseResumeParser):
    """Extracts structural text, headings, tables, and metadata from DOCX resumes."""

    def supports(self, mime_type: str, filename: str) -> bool:
        """Check if parser handles DOCX documents."""
        clean_mime = (mime_type or "").lower().strip()
        clean_name = (filename or "").lower().strip()
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return clean_mime == docx_mime or clean_name.endswith(".docx")

    async def parse(self, content_bytes: bytes, filename: str) -> ParsedResumeResult:
        """Parse DOCX binary asynchronously."""
        return await asyncio.to_thread(self._sync_parse, content_bytes, filename)

    def _sync_parse(self, content_bytes: bytes, filename: str) -> ParsedResumeResult:
        warnings: list[str] = []
        doc_metadata: dict[str, str] = {}
        paragraphs: list[str] = []
        tables_data: list[list[list[str]]] = []

        try:
            doc = docx.Document(io.BytesIO(content_bytes))
        except Exception as exc:
            return ParsedResumeResult(
                raw_text="",
                structured_content={},
                template_metadata={"file_type": "docx", "parser": "DocxParser (python-docx)"},
                preservation_capability=PreservationCapability.UNSUPPORTED,
                extraction_warnings=[f"Failed to open DOCX archive: {exc}"],
                is_valid=False,
            )

        # 1. Extract core properties/metadata
        try:
            core_props = doc.core_properties
            if core_props:
                if core_props.title:
                    doc_metadata["title"] = core_props.title
                if core_props.author:
                    doc_metadata["author"] = core_props.author
                if core_props.last_modified_by:
                    doc_metadata["last_modified_by"] = core_props.last_modified_by
        except Exception as exc:
            warnings.append(f"Metadata extraction warning: {exc}")

        # 2. Extract paragraph text
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                paragraphs.append(text)

        # 3. Extract table text
        for table in doc.tables:
            table_rows: list[list[str]] = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    table_rows.append(row_cells)
                    # Also append row text to paragraphs for section heuristics
                    paragraphs.append(" | ".join(row_cells))
            if table_rows:
                tables_data.append(table_rows)

        raw_text = "\n\n".join(paragraphs).strip()

        if not raw_text:
            warnings.append("DOCX document contains no readable text content.")
            return ParsedResumeResult(
                raw_text="",
                structured_content={},
                template_metadata={"file_type": "docx", "parser": "DocxParser (python-docx)"},
                preservation_capability=PreservationCapability.UNSUPPORTED,
                extraction_warnings=warnings,
                is_valid=False,
            )

        # 4. Extract structured sections
        structured_content = extract_deterministic_sections(raw_text)

        # DOCX layout preservation is limited without native Word layout engine
        capability = PreservationCapability.LIMITED

        template_metadata = {
            "file_type": "docx",
            "filename": filename,
            "paragraph_count": len(doc.paragraphs),
            "table_count": len(doc.tables),
            "document_metadata": doc_metadata,
            "parser": "DocxParser (python-docx)",
            "preservation_capability": capability.value,
        }

        return ParsedResumeResult(
            raw_text=raw_text,
            structured_content=structured_content,
            template_metadata=template_metadata,
            preservation_capability=capability,
            extraction_warnings=warnings,
            is_valid=True,
        )
