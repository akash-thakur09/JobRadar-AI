"""Settings API persistence and write-only SMTP authentication regressions."""

import pytest

from app.core.runtime_settings import get_runtime_settings


@pytest.mark.unit
async def test_saved_settings_are_shared_and_never_return_smtp_password(
    async_client, monkeypatch, tmp_path
):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    updated = await async_client.patch(
        "/api/v1/settings",
        json={
            "notification_recipient_email": "candidate@example.test",
            "pipeline_scheduler_enabled": True,
            "smtp_host": "smtp.example.test",
            "smtp_username": "qa",
            "smtp_use_tls": True,
            "smtp_password": "fixture-secret",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["smtp_password_configured"]
    assert "fixture-secret" not in updated.text
    assert get_runtime_settings().smtp_password == "fixture-secret"

    moved = await async_client.patch("/api/v1/settings", json={"smtp_host": "other.example.test"})
    assert moved.status_code == 200, moved.text
    assert not moved.json()["smtp_password_configured"]
    saved = (await async_client.get("/api/v1/settings")).json()
    assert saved["notification_recipient_email"] == "candidate@example.test"
    assert saved["pipeline_scheduler_enabled"] is True
    assert get_runtime_settings().smtp_password == ""
