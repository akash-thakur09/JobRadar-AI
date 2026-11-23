"""Unit tests for Resume Management REST API endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import EntityAlreadyExistsError
from app.database.session import get_db_session
from app.main import create_app
from app.modules.resumes.models import MasterResume, ResumeVersion
from app.modules.resumes.schemas import PaginationMetadata
from app.modules.resumes.service import get_resume_service


@pytest.fixture
def sample_resume() -> MasterResume:
    """Return a sample MasterResume instance."""
    now = datetime.now(UTC)
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    resume = MasterResume(
        id=resume_id,
        candidate_profile_id=candidate_id,
        original_filename="engineer_resume.pdf",
        storage_key=f"resumes/raw/{candidate_id}/{resume_id}.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="fakechecksum1234567890abcdef",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    version = ResumeVersion(
        id=uuid.uuid4(),
        master_resume_id=resume_id,
        version_number=1,
        structured_content={"skills": ["Python", "Docker"], "summary": "Senior engineer"},
        template_metadata={"page_count": 1, "preservation_capability": "SUPPORTED"},
        checksum_sha256="fakeversionchecksum1234",
        is_valid=True,
        processing_status="COMPLETED",
        created_at=now,
        updated_at=now,
    )
    resume.versions = [version]
    return resume


@pytest.mark.asyncio
async def test_list_resumes_endpoint(sample_resume: MasterResume) -> None:
    """GET /api/v1/resumes returns paginated resume summaries."""
    app = create_app()
    mock_service = AsyncMock()
    pagination = PaginationMetadata(
        page=1,
        page_size=20,
        total_items=1,
        total_pages=1,
        has_next=False,
        has_prev=False,
    )
    mock_service.list_resumes.return_value = ([sample_resume], pagination)

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/resumes")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["original_filename"] == "engineer_resume.pdf"


@pytest.mark.asyncio
async def test_upload_resume_endpoint_success(sample_resume: MasterResume) -> None:
    """POST /api/v1/resumes/upload creates resume and returns 201 Created."""
    app = create_app()
    mock_service = AsyncMock()
    version = sample_resume.versions[0]
    mock_service.upload_resume.return_value = (sample_resume, version)

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("my_resume.pdf", b"%PDF-1.4 dummy valid stream", "application/pdf")}
        response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == str(sample_resume.id)
    assert data["original_filename"] == "engineer_resume.pdf"
    assert data["active_version"]["processing_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_upload_resume_duplicate_conflict() -> None:
    """POST /api/v1/resumes/upload with identical checksum raises 409 Conflict."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.upload_resume.side_effect = EntityAlreadyExistsError(
        entity_name="MasterResume", identifier="checksum:duplicate"
    )

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("my_resume.pdf", b"%PDF-1.4 duplicate stream", "application/pdf")}
        response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["status"] == 409
    assert "already exists" in data["detail"]


@pytest.mark.asyncio
async def test_get_resume_detail_endpoint(sample_resume: MasterResume) -> None:
    """GET /api/v1/resumes/{id} returns resume metadata and versions."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.get_resume.return_value = sample_resume

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{sample_resume.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(sample_resume.id)
    assert data["is_active"] is True
    assert len(data["versions"]) == 1


@pytest.mark.asyncio
async def test_activate_resume_endpoint(sample_resume: MasterResume) -> None:
    """POST /api/v1/resumes/{id}/activate sets resume as active."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.activate_resume.return_value = sample_resume

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/resumes/{sample_resume.id}/activate")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_resume_versions_endpoint(sample_resume: MasterResume) -> None:
    """GET /api/v1/resumes/{id}/versions returns list of versions."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.list_versions.return_value = sample_resume.versions

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{sample_resume.id}/versions")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["version_number"] == 1


@pytest.mark.asyncio
async def test_download_resume_endpoint(sample_resume: MasterResume) -> None:
    """GET /api/v1/resumes/{id}/download returns file binary with attachment header."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.download_resume_file.return_value = (
        b"%PDF-1.4 binary content",
        "application/pdf",
        "resume.pdf",
    )

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{sample_resume.id}/download")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="resume.pdf"' in response.headers["content-disposition"]
    assert "filename*=UTF-8''resume.pdf" in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.4 binary content"


@pytest.mark.asyncio
async def test_download_resume_unicode_en_dash_docx(sample_resume: MasterResume) -> None:
    """DOCX filename containing an en dash (\u2013) downloads successfully without HTTP 500."""
    app = create_app()
    mock_service = AsyncMock()
    docx_bytes = b"PK\x03\x04\x14\x00\x06\x00 dummy valid docx binary content"
    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    unicode_filename = "Akash Thakur \u2013 Resume.docx"

    mock_service.download_resume_file.return_value = (
        docx_bytes,
        docx_mime,
        unicode_filename,
    )

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{sample_resume.id}/download")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == docx_mime
    assert response.content == docx_bytes

    cd_header = response.headers["content-disposition"]
    assert 'filename="Akash Thakur - Resume.docx"' in cd_header
    assert "filename*=UTF-8''Akash%20Thakur%20%E2%80%93%20Resume.docx" in cd_header
    cd_header.encode("latin-1")


@pytest.mark.asyncio
async def test_download_resume_spaces_and_parentheses(sample_resume: MasterResume) -> None:
    """Filename containing spaces and parentheses encodes properly."""
    app = create_app()
    mock_service = AsyncMock()
    pdf_bytes = b"%PDF-1.4 spaces and parens"
    filename = "Senior Architect Resume (2026).pdf"

    mock_service.download_resume_file.return_value = (
        pdf_bytes,
        "application/pdf",
        filename,
    )

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{sample_resume.id}/download")

    assert response.status_code == status.HTTP_200_OK
    cd_header = response.headers["content-disposition"]
    assert 'filename="Senior Architect Resume (2026).pdf"' in cd_header
    assert "filename*=UTF-8''Senior%20Architect%20Resume%20%282026%29.pdf" in cd_header
    assert response.content == pdf_bytes


@pytest.mark.asyncio
async def test_download_resume_non_latin_unicode(sample_resume: MasterResume) -> None:
    """Non-Latin Unicode filenames provide a valid ASCII fallback and preserved UTF-8 filename*."""
    app = create_app()
    mock_service = AsyncMock()
    binary_content = b"%PDF-1.4 non-latin content"
    filename = "\u7b80\u5386.pdf"

    mock_service.download_resume_file.return_value = (
        binary_content,
        "application/pdf",
        filename,
    )

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{sample_resume.id}/download")

    assert response.status_code == status.HTTP_200_OK
    cd_header = response.headers["content-disposition"]
    assert 'filename="resume.pdf"' in cd_header
    assert "filename*=UTF-8''%E7%AE%80%E5%8E%86.pdf" in cd_header
    assert response.content == binary_content
    cd_header.encode("latin-1")


@pytest.mark.asyncio
async def test_download_resume_crlf_header_injection_prevention(sample_resume: MasterResume) -> None:
    """Filename containing CR/LF cannot inject additional headers into the response."""
    app = create_app()
    mock_service = AsyncMock()
    malicious_filename = "resume\r\nInjected-Header: malicious_payload\r\nfile.pdf"

    mock_service.download_resume_file.return_value = (
        b"%PDF-1.4 dummy",
        "application/pdf",
        malicious_filename,
    )

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{sample_resume.id}/download")

    assert response.status_code == status.HTTP_200_OK
    assert "injected-header" not in response.headers
    cd_header = response.headers["content-disposition"]
    assert "\r" not in cd_header
    assert "\n" not in cd_header


@pytest.mark.asyncio
async def test_get_resume_content_endpoint() -> None:
    """GET /api/v1/resumes/{id}/content returns structured JSON content."""
    app = create_app()
    mock_service = AsyncMock()
    resume_id = uuid.uuid4()
    mock_service.get_resume_content.return_value = {
        "skills": ["Python", "FastAPI"],
        "summary": "Cloud Architect",
    }

    app.dependency_overrides[get_resume_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/resumes/{resume_id}/content")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["skills"] == ["Python", "FastAPI"]
