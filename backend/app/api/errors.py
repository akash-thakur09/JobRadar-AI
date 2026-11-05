"""Centralized error handling and RFC 7807 Problem Details response formatting."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.core.logging import get_correlation_id

logger = logging.getLogger(__name__)


def create_problem_details_response(
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    error_type: str = "about:blank",
    invalid_params: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Format and return an RFC 7807 compliant JSONResponse."""
    correlation_id = get_correlation_id()
    problem_type = (
        f"https://api.jobradar.ai/v1/errors/{error_type}"
        if not error_type.startswith("http")
        else error_type
    )

    payload: dict[str, Any] = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
        "correlation_id": correlation_id,
    }

    if invalid_params:
        payload["invalid_params"] = invalid_params

    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers on the FastAPI app instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application exception [%s]: %s (path=%s)",
            exc.error_type,
            exc.message,
            request.url.path,
        )
        return create_problem_details_response(
            request=request,
            status_code=exc.status_code,
            title=exc.error_type.replace("-", " ").title(),
            detail=exc.message,
            error_type=exc.error_type,
            invalid_params=exc.invalid_params,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        invalid_params: list[dict[str, Any]] = []
        for error in exc.errors():
            field_name = " -> ".join(str(loc) for loc in error.get("loc", []))
            invalid_params.append(
                {
                    "name": field_name,
                    "reason": error.get("msg", "Invalid value"),
                    "type": error.get("type", "value_error"),
                }
            )

        logger.info(
            "Validation error on %s: %d invalid parameters", request.url.path, len(invalid_params)
        )
        return create_problem_details_response(
            request=request,
            status_code=getattr(
                status,
                "HTTP_422_UNPROCESSABLE_CONTENT",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ),
            title="Validation Error",
            detail="The request body or parameters failed schema validation.",
            error_type="validation-error",
            invalid_params=invalid_params,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.info("HTTP exception: %s %s", exc.status_code, exc.detail)
        return create_problem_details_response(
            request=request,
            status_code=exc.status_code,
            title="HTTP Error",
            detail=str(exc.detail),
            error_type="http-error",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled server exception on %s: %s",
            request.url.path,
            str(exc),
            exc_info=True,
        )
        return create_problem_details_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal Server Error",
            detail="An unexpected internal server error occurred. Please reference the correlation ID.",
            error_type="internal-server-error",
        )
