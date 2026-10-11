"""Response envelope (spec Section 19.1)."""
import datetime as dt
from typing import Any

from fastapi.responses import JSONResponse

from app.platform.errors import ApiError
from app.platform.requestctx import current_request_id
from app.platform.serialize import iso, to_json


def meta(with_timestamp: bool = True) -> dict[str, str]:
    m = {"api_version": "v1", "request_id": current_request_id()}
    if with_timestamp:
        m["timestamp"] = iso(dt.datetime.now(dt.UTC))
    return m


def success_body(data: Any, message: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"success": True}
    if message:
        body["message"] = message
    body["data"] = to_json(data)
    body["meta"] = meta()
    return body


def ok(data: Any, message: str | None = None, status: int = 200, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(success_body(data, message), status_code=status, headers=headers)


def error_body(err: ApiError) -> dict[str, Any]:
    return {"success": False,
            "error": {"code": err.code, "message": err.message, "retryable": err.retryable, "details": to_json(err.details)},
            "meta": meta(with_timestamp=False)}


def error_response(err: ApiError) -> JSONResponse:
    return JSONResponse(error_body(err), status_code=err.status, headers=err.headers or None)
