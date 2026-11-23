"""Operator configuration and connectivity checks."""

import asyncio
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.runtime_settings import (
    RuntimeSettingsUpdate,
    RuntimeSettingsView,
    get_runtime_settings,
    save_runtime_settings,
)
from app.modules.matching.llm.factory import get_llm_provider
from app.modules.notifications.email.factory import get_email_provider
from app.modules.pipeline.scheduler import SCHEDULER_LEADER_LOCK

router = APIRouter(prefix="/settings", tags=["Settings"])


class ConnectionCheck(BaseModel):
    ok: bool
    message: str


async def _public_settings(settings: Settings) -> RuntimeSettingsView:
    lock_held = None
    try:
        async with Redis.from_url(settings.redis_url) as redis:
            lock_held = bool(await asyncio.wait_for(redis.exists(SCHEDULER_LEADER_LOCK), timeout=2))
    except (RedisError, OSError, TimeoutError):
        pass
    values = settings.model_dump(include=set(RuntimeSettingsView.model_fields))
    values.update(
        smtp_username=settings.effective_smtp_username,
        smtp_password_configured=bool(settings.smtp_password),
        scheduler_lock_held=lock_held,
    )
    return RuntimeSettingsView.model_validate(values)


@router.get("", response_model=RuntimeSettingsView)
async def read_settings() -> RuntimeSettingsView:
    return await _public_settings(await asyncio.to_thread(get_runtime_settings))


@router.patch("", response_model=RuntimeSettingsView)
async def update_settings(request: RuntimeSettingsUpdate) -> RuntimeSettingsView:
    return await _public_settings(await asyncio.to_thread(save_runtime_settings, request))


@router.post("/test/{service}", response_model=ConnectionCheck)
async def test_connection(service: Literal["ollama", "smtp"]) -> ConnectionCheck:
    provider = get_llm_provider() if service == "ollama" else get_email_provider()
    ok = await provider.ping()
    label = "Ollama" if service == "ollama" else "Email provider"
    return ConnectionCheck(
        ok=ok,
        message=f"{label} connection succeeded." if ok else f"{label} connection failed.",
    )
