"""Operator overrides shared by the API and workers through application storage."""

import os
import tempfile
import threading
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from app.core.config import Settings, get_settings

RecipientAddress = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, max_length=255, pattern=r"^(?:[^\s@<>,]+@[^\s@<>,]+\.[^\s@<>,]+)?$"
    ),
]
SMTPHost = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, max_length=253, pattern=r"^[A-Za-z0-9][A-Za-z0-9.:-]*$"
    ),
]
_settings_write_lock = threading.Lock()


class RuntimeOptions(BaseModel):
    """The settings operators can change without restarting services."""

    model_config = ConfigDict(extra="forbid")

    ollama_model: str | None = Field(None, min_length=1, max_length=200)
    llm_timeout_seconds: float | None = Field(None, ge=1, le=180)
    pipeline_scheduler_enabled: bool | None = None
    pipeline_discovery_interval_hours: int | None = Field(None, ge=1, le=720)
    email_provider: str | None = Field(None, pattern=r"^(smtp|mock)$")
    smtp_host: SMTPHost | None = None
    smtp_port: int | None = Field(None, ge=1, le=65535)
    smtp_username: str | None = Field(None, max_length=255, pattern=r"^[^\r\n]*$")
    smtp_from_email: RecipientAddress | None = Field(None, min_length=3)
    smtp_use_tls: bool | None = None
    notification_recipient_email: RecipientAddress | None = None


class RuntimeSettingsUpdate(RuntimeOptions):
    smtp_password: SecretStr | None = Field(None, max_length=1024)


class RuntimeSettingsView(BaseModel):
    ollama_model: str
    ollama_base_url: str
    llm_provider: str
    llm_timeout_seconds: float
    pipeline_scheduler_enabled: bool
    pipeline_discovery_interval_hours: int
    scheduler_lock_held: bool | None
    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_from_email: str
    smtp_use_tls: bool
    smtp_password_configured: bool
    notification_recipient_email: str
    career_page_allowed_hosts: list[str]


class StoredRuntimeOptions(RuntimeOptions):
    smtp_password: str | None = Field(None, max_length=1024, repr=False)


def _path(settings: Settings) -> Path:
    return Path(settings.storage_dir) / ".settings" / "runtime.json"


def _read(path: Path) -> StoredRuntimeOptions:
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return StoredRuntimeOptions()
    return StoredRuntimeOptions.model_validate_json(contents)


def get_runtime_settings() -> Settings:
    """Load the effective settings on demand so all processes see saved changes."""
    defaults = get_settings()
    return _apply_overrides(defaults, _read(_path(defaults)).model_dump(exclude_none=True))


def save_runtime_settings(request: RuntimeSettingsUpdate) -> Settings:
    with _settings_write_lock:
        return _save_runtime_settings(request)


def _apply_overrides(defaults: Settings, overrides: dict[str, object]) -> Settings:
    if "smtp_username" in overrides:
        overrides = {"smtp_user": "", **overrides}
    return defaults.model_copy(update=overrides)


def _save_runtime_settings(request: RuntimeSettingsUpdate) -> Settings:
    defaults = get_settings()
    path = _path(defaults)
    existing = _read(path).model_dump(exclude_none=True)
    effective = _apply_overrides(defaults, existing)
    update = request.model_dump(exclude_none=True, exclude={"smtp_password"})
    # Never carry an existing password over to a different server, port or account.
    mail_identity = {
        "smtp_host": effective.smtp_host,
        "smtp_port": effective.smtp_port,
        "smtp_username": effective.effective_smtp_username,
        "smtp_use_tls": effective.smtp_use_tls,
    }
    if request.smtp_password is not None:
        update["smtp_password"] = request.smtp_password.get_secret_value()
    elif any(field in update and update[field] != value for field, value in mail_identity.items()):
        update["smtp_password"] = ""
    merged = StoredRuntimeOptions.model_validate({**existing, **update})
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, mode="w", encoding="utf-8", delete=False
    ) as temporary:
        try:
            temporary.write(merged.model_dump_json(exclude_none=True))
            temporary.close()
            os.replace(temporary.name, path)
        finally:
            Path(temporary.name).unlink(missing_ok=True)
    return _apply_overrides(defaults, merged.model_dump(exclude_none=True))
