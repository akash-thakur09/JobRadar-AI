"""Unit tests for storage abstraction and LocalFileStorage."""

import tempfile
from pathlib import Path

import pytest

from app.infrastructure.storage.local import LocalFileStorage


@pytest.fixture
def temp_storage() -> LocalFileStorage:
    """Provide a LocalFileStorage instance backed by a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield LocalFileStorage(base_dir=tmp_dir)


@pytest.mark.asyncio
async def test_save_and_read(temp_storage: LocalFileStorage) -> None:
    """Verify storing bytes and reading them back."""
    key = "resumes/candidate1/test.pdf"
    content = b"%PDF-1.4 sample content"

    saved_key = await temp_storage.save(key, content, content_type="application/pdf")
    assert saved_key == key

    read_bytes = await temp_storage.read(key)
    assert read_bytes == content


@pytest.mark.asyncio
async def test_exists_and_delete(temp_storage: LocalFileStorage) -> None:
    """Verify exists check and file deletion."""
    key = "documents/sample.docx"
    content = b"PK\x03\x04 dummy docx"

    assert await temp_storage.exists(key) is False

    await temp_storage.save(key, content)
    assert await temp_storage.exists(key) is True

    await temp_storage.delete(key)
    assert await temp_storage.exists(key) is False


@pytest.mark.asyncio
async def test_read_non_existent_file_raises_error(temp_storage: LocalFileStorage) -> None:
    """Verify reading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        await temp_storage.read("does/not/exist.pdf")


@pytest.mark.parametrize(
    "malicious_key",
    [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
        "sub/../../secret.txt",
    ],
)
@pytest.mark.asyncio
async def test_path_traversal_prevention(
    temp_storage: LocalFileStorage, malicious_key: str
) -> None:
    """Verify path traversal keys are rejected with ValueError."""
    with pytest.raises(ValueError, match="Path traversal detected"):
        await temp_storage.save(malicious_key, b"evil payload")

    with pytest.raises(ValueError, match="Path traversal detected"):
        await temp_storage.read(malicious_key)


def test_get_path_resolves_to_base_dir(temp_storage: LocalFileStorage) -> None:
    """Verify get_path returns an absolute path within base_dir."""
    key = "resumes/raw/file.pdf"
    path_str = temp_storage.get_path(key)
    path = Path(path_str)
    assert path.is_absolute()
    assert str(path).startswith(str(temp_storage.base_dir))
