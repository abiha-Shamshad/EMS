"""ASGI middleware, JSON logging and exception handlers (spec Sections 19.1, 32, 33)."""
import json
import logging
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.platform.errors import ApiError
from app.platform.requestctx import log_fields_var, new_request_id, request_id_var
from app.platform.responses import error_response

log = logging.getLogger("ems")


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Callers pass only safe fields: never bodies, cookies, tokens, passwords or emails."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"), "level": record.levelname.lower(),
                                 "logger": record.name, "message": record.getMessage()}
        entry.update(getattr(record, "fields", {}) or {})
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


class RequestMiddleware:
    """Request ID, access log line and security headers for every HTTP response."""

    def __init__(self, app, csp: str, hsts: bool):
        self.app = app
        self.headers = [(b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"same-origin"),
                        (b"content-security-policy", csp.encode())]
        if hsts:
            self.headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = new_request_id()
        fields = {"request_id": request_id, "method": scope["method"], "route": scope["path"]}
        token_rid, token_fields = request_id_var.set(request_id), log_fields_var.set(fields)
        started, status = time.perf_counter(), 500

        async def send_wrapper(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [*message.get("headers", []), *self.headers, (b"x-request-id", request_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            fields.update(status=status, duration_ms=round((time.perf_counter() - started) * 1000, 1))
            route = scope.get("route")
            if route is not None:
                fields["route"] = getattr(route, "path", scope["path"])     # template, so IDs are not logged
            log.info("request", extra={"fields": fields})
            request_id_var.reset(token_rid)
            log_fields_var.reset(token_fields)


def _field_path(loc: tuple) -> str:
    parts = [p for p in loc if p not in ("body", "query", "path", "header")]
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out or "request"


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields = {}
        for e in exc.errors():
            fields.setdefault(_field_path(tuple(e.get("loc", ()))), e.get("msg", "Invalid value."))
        return error_response(ApiError("VALIDATION_FAILED", "Check the highlighted fields.", {"fields": fields}))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        if exc.status_code in (404, 405):
            return error_response(ApiError("NOT_FOUND", "Not found."))
        return error_response(ApiError("VALIDATION_FAILED", str(exc.detail)))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        log.error("unhandled error", exc_info=exc, extra={"fields": dict(log_fields_var.get() or {})})
        return error_response(ApiError("INTERNAL_ERROR", "Something went wrong. Quote the request ID if you contact support."))
