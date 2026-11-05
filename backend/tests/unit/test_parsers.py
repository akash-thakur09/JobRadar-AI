"""Unit tests for resume parsing engine and file validation."""

import io

import docx
import pypdf
import pytest

from app.modules.resumes.parsers.base import PreservationCapability
from app.modules.resumes.parsers.docx import DocxParser
from app.modules.resumes.parsers.pdf import PdfParser
from app.modules.resumes.parsers.registry import get_parser_for_mime_type
from app.modules.resumes.schemas import validate_resume_file


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF byte stream with text content."""
    return b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 200 >>
stream
BT
/F1 12 Tf
72 712 Td
(Jane Doe) Tj
0 -20 Td
(Email: jane.doe@example.com) Tj
0 -20 Td
(Phone: 555-019-2834) Tj
0 -20 Td
(PROFESSIONAL SUMMARY) Tj
0 -20 Td
(Senior Cloud Engineer with deep distributed systems experience.) Tj
0 -20 Td
(SKILLS) Tj
0 -20 Td
(Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL) Tj
0 -20 Td
(EXPERIENCE) Tj
0 -20 Td
(Lead Architect at TechCorp 2020-Present) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000244 00000 n
0000000318 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
570
%%EOF"""


@pytest.fixture
def sample_docx_bytes() -> bytes:
    """Generate a valid DOCX byte stream with paragraphs and tables."""
    doc = docx.Document()
    doc.add_heading("Jane Doe", level=0)
    doc.add_paragraph("Email: jane.doe@example.com | Phone: 555-019-2834")
    doc.add_heading("SUMMARY", level=1)
    doc.add_paragraph("Principal Software Architect with 10 years experience.")
    doc.add_heading("TECHNICAL SKILLS", level=1)
    doc.add_paragraph("Python, Go, PostgreSQL, Redis, Kubernetes")
    doc.add_heading("WORK EXPERIENCE", level=1)
    doc.add_paragraph("Staff Engineer at Global Systems Inc (2021-2026)")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Degree"
    table.cell(0, 1).text = "Institution"
    table.cell(1, 0).text = "B.S. Computer Science"
    table.cell(1, 1).text = "Stanford University"

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def blank_pdf_bytes() -> bytes:
    """Generate a blank PDF representing a scanned/image-only document without text."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ==============================================================================
# Validation Tests
# ==============================================================================


def test_validate_resume_file_valid_pdf(sample_pdf_bytes: bytes) -> None:
    """Verify validation passes for valid PDF."""
    mime = validate_resume_file("resume.pdf", sample_pdf_bytes, "application/pdf")
    assert mime == "application/pdf"


def test_validate_resume_file_valid_docx(sample_docx_bytes: bytes) -> None:
    """Verify validation passes for valid DOCX."""
    mime = validate_resume_file("resume.docx", sample_docx_bytes, None)
    assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_validate_resume_file_empty() -> None:
    """Verify empty file is rejected."""
    with pytest.raises(ValueError, match="empty"):
        validate_resume_file("test.pdf", b"", "application/pdf")


def test_validate_resume_file_oversized() -> None:
    """Verify file exceeding size limit is rejected."""
    oversized = b"%PDF-" + b"x" * (11 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds maximum allowed size"):
        validate_resume_file("large.pdf", oversized, "application/pdf")


def test_validate_resume_file_invalid_extension() -> None:
    """Verify unsupported extensions are rejected."""
    with pytest.raises(ValueError, match="Unsupported file extension"):
        validate_resume_file("resume.txt", b"plain text", "text/plain")


def test_validate_resume_file_invalid_magic_bytes_pdf() -> None:
    """Verify PDF with invalid magic header is rejected."""
    with pytest.raises(ValueError, match="Invalid PDF file signature"):
        validate_resume_file("fake.pdf", b"NOT_A_PDF_STREAM", "application/pdf")


def test_validate_resume_file_invalid_magic_bytes_docx() -> None:
    """Verify DOCX with invalid magic header is rejected."""
    with pytest.raises(ValueError, match="Invalid DOCX file signature"):
        validate_resume_file("fake.docx", b"NOT_A_ZIP_HEADER", None)


# ==============================================================================
# Parser Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_pdf_parser_success(sample_pdf_bytes: bytes) -> None:
    """Verify PDF parser extracts text, layout fonts, and structured sections."""
    parser = PdfParser()
    assert parser.supports("application/pdf", "resume.pdf") is True

    result = await parser.parse(sample_pdf_bytes, "resume.pdf")

    assert result.is_valid is True
    assert "Jane Doe" in result.raw_text
    assert result.structured_content["contact"]["email"] == "jane.doe@example.com"
    assert "Python" in result.structured_content["skills"]
    assert result.preservation_capability in (
        PreservationCapability.SUPPORTED,
        PreservationCapability.LIMITED,
    )
    assert result.template_metadata["page_count"] == 1


@pytest.mark.asyncio
async def test_pdf_parser_scanned_detection(blank_pdf_bytes: bytes) -> None:
    """Verify blank or scanned PDF is detected with warnings and invalid flag."""
    parser = PdfParser()
    result = await parser.parse(blank_pdf_bytes, "scanned.pdf")

    assert result.is_valid is False
    assert result.preservation_capability == PreservationCapability.UNSUPPORTED
    assert any("scanned or image-based" in w for w in result.extraction_warnings)


@pytest.mark.asyncio
async def test_pdf_parser_corrupted_bytes() -> None:
    """Verify corrupted PDF stream returns invalid result without unhandled crash."""
    parser = PdfParser()
    corrupt_pdf = b"%PDF-1.4 CORRUPTED BINARY CONTENT !!!"
    result = await parser.parse(corrupt_pdf, "corrupt.pdf")

    assert result.is_valid is False


@pytest.mark.asyncio
async def test_docx_parser_success(sample_docx_bytes: bytes) -> None:
    """Verify DOCX parser extracts paragraphs, tables, and structured sections."""
    parser = DocxParser()
    assert (
        parser.supports(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "cv.docx"
        )
        is True
    )

    result = await parser.parse(sample_docx_bytes, "cv.docx")

    assert result.is_valid is True
    assert "Jane Doe" in result.raw_text
    assert result.structured_content["contact"]["email"] == "jane.doe@example.com"
    assert result.preservation_capability == PreservationCapability.LIMITED
    assert result.template_metadata["table_count"] == 1


@pytest.mark.asyncio
async def test_docx_parser_corrupted_archive() -> None:
    """Verify corrupted DOCX archive returns invalid result safely."""
    parser = DocxParser()
    corrupted_docx = b"PK\x03\x04 CORRUPTED_ZIP_ENTRY"
    result = await parser.parse(corrupted_docx, "broken.docx")

    assert result.is_valid is False
    assert result.preservation_capability == PreservationCapability.UNSUPPORTED


def test_parser_registry_selection() -> None:
    """Verify dynamic selection of parsers based on MIME types and filenames."""
    pdf_parser = get_parser_for_mime_type("application/pdf", "resume.pdf")
    assert isinstance(pdf_parser, PdfParser)

    docx_parser = get_parser_for_mime_type(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "resume.docx"
    )
    assert isinstance(docx_parser, DocxParser)

    with pytest.raises(ValueError, match="No parser available"):
        get_parser_for_mime_type("image/png", "scan.png")
