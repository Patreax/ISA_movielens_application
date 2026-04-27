"""Custom exceptions and FastAPI exception handlers.

Maps every error path to the ErrorResponse shape from contracts/openapi.yaml
and data-model.md.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger


class UserNotFoundError(Exception):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"user_id {user_id!r} not found in MovieLens dataset")
        self.user_id = user_id


class InferenceError(Exception):
    def __init__(self, model: str, cause: Exception) -> None:
        super().__init__(f"{model} inference failed: {cause}")
        self.model = model
        self.cause = cause


class ServiceStartingError(Exception):
    pass


def _error_payload(error: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": error, "message": message}
    if details is not None:
        payload["details"] = details
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UserNotFoundError)
    async def _user_not_found(request: Request, exc: UserNotFoundError):
        logger.info(f"user_not_found: {exc.user_id}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error_payload(
                "user_not_found",
                f"user_id {exc.user_id!r} not found",
            ),
        )

    @app.exception_handler(InferenceError)
    async def _inference_failed(request: Request, exc: InferenceError):
        logger.exception(f"inference_failed in {exc.model}: {exc.cause}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                "inference_failed",
                f"{exc.model} inference failed",
                details={"model": exc.model, "cause": str(exc.cause)},
            ),
        )

    @app.exception_handler(ServiceStartingError)
    async def _starting(request: Request, exc: ServiceStartingError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_error_payload(
                "service_starting",
                "service is still starting; try again shortly",
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        field_errors: list[dict[str, Any]] = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p != "body"]
            field_path = ".".join(loc) if loc else "<root>"
            entry: dict[str, Any] = {
                "field": field_path,
                "message": err.get("msg", "invalid"),
            }
            ctx = err.get("ctx") or {}
            expected = ctx.get("expected")
            if expected is not None:
                entry["accepted"] = [str(expected)]
            field_errors.append(entry)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(
                "validation_error",
                "request validation failed",
                details={"field_errors": field_errors},
            ),
        )
