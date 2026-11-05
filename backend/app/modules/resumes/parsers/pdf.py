"""PDF structural extractor using pdfplumber and pypdf."""

import asyncio
import io
import logging

import pdfplumber
import pypdf

from app.modules.resumes.parsers.base import (
    BaseResumeParser,
    ParsedResumeResult,
    PreservationCapability,
    extract_deterministic_sections,
)

logger = logging.getLogger(__name__)


class PdfParser(BaseResumeParser):
    """Extracts structural text, page layout, and font metadata from PDF resumes."""

    def supports(self, mime_type: str, filename: str) -> bool:
        """Check if parser handles PDF documents."""
        clean_mime = (mime_type or "").lower().strip()
        clean_name = (filename or "").lower().strip()
        return clean_mime == "application/pdf" or clean_name.endswith(".pdf")

    async def parse(self, content_bytes: bytes, filename: str) -> ParsedResumeResult:
        """Parse PDF binary asynchronously."""
        return await asyncio.to_thread(self._sync_parse, content_bytes, filename)

    def _sync_parse(self, content_bytes: bytes, filename: str) -> ParsedResumeResult:
        warnings: list[str] = []
        page_texts: list[str] = []
        fonts_detected: set[str] = set()
        page_count = 0
        doc_metadata: dict[str, str] = {}

        # 1. First pass: extract basic metadata & page count via pypdf
        try:
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            page_count = len(reader.pages)
            if reader.metadata:
                for k, v in reader.metadata.items():
                    if isinstance(v, str) and v.strip():
                        clean_key = k.lstrip("/").lower()
                        doc_metadata[clean_key] = v.strip()
        except Exception as exc:
            logger.warning("pypdf metadata extraction warning for %s: %s", filename, exc)
            warnings.append(f"Metadata extraction warning: {exc}")

        # 2. Extract detailed text and layout fonts via pdfplumber
        try:
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                page_count = max(page_count, len(pdf.pages))
                for _page_idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    page_texts.append(text)

                    # Extract character fonts if present
                    if hasattr(page, "chars") and page.chars:
                        for char in page.chars:
                            font_name = char.get("fontname")
                            if font_name and isinstance(font_name, str):
                                fonts_detected.add(font_name)
        except Exception as exc:
            logger.warning("pdfplumber extraction failed, falling back to pypdf: %s", exc)
            warnings.append(f"pdfplumber extraction warning: {exc}")
            # Fallback extraction via pypdf
            try:
                reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                page_texts = [page.extract_text() or "" for page in reader.pages]
            except Exception as fallback_exc:
                return ParsedResumeResult(
                    raw_text="",
                    structured_content={},
                    template_metadata={
                        "file_type": "pdf",
                        "page_count": page_count,
                        "parser": "pdfplumber+pypdf",
                    },
                    preservation_capability=PreservationCapability.UNSUPPORTED,
                    extraction_warnings=[f"Fatal PDF parsing failure: {fallback_exc}"],
                    is_valid=False,
                )

        raw_text = "\n\n".join(page_texts).strip()

        # 3. Detect scanned / image-only PDFs
        is_scanned = False
        if len(raw_text) < 50:
            is_scanned = True
            warnings.append(
                "Document contains little or no extractable text. It appears to be scanned or image-based; OCR is not supported in this milestone."
            )

        # 4. Determine template preservation capability
        if is_scanned or not raw_text:
            capability = PreservationCapability.UNSUPPORTED
        elif len(fonts_detected) > 0 and len(raw_text) > 200:
            capability = PreservationCapability.SUPPORTED
        else:
            capability = PreservationCapability.LIMITED

        # 5. Extract structured sections
        structured_content = extract_deterministic_sections(raw_text)

        template_metadata = {
            "file_type": "pdf",
            "page_count": page_count,
            "fonts": sorted(fonts_detected)[:20],
            "is_scanned": is_scanned,
            "document_metadata": doc_metadata,
            "parser": "PdfParser (pdfplumber 0.11)",
            "preservation_capability": capability.value,
        }

        return ParsedResumeResult(
            raw_text=raw_text,
            structured_content=structured_content,
            template_metadata=template_metadata,
            preservation_capability=capability,
            extraction_warnings=warnings,
            is_valid=not is_scanned and bool(raw_text),
        )
