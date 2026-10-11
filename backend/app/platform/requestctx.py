"""Per-request values shared with logging and response envelopes (set by the request middleware).

`log_fields` holds one mutable dict per request: the middleware creates it and the request pipeline fills in org_id and
user_id, so the access log line written by the middleware can include them.
"""
import contextvars
import secrets

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
log_fields_var: contextvars.ContextVar[dict | None] = contextvars.ContextVar("log_fields", default=None)


def new_request_id() -> str:
    return "req_" + secrets.token_hex(6)


def current_request_id() -> str:
    return request_id_var.get() or new_request_id()


def set_log_field(name: str, value: str) -> None:
    fields = log_fields_var.get()
    if fields is not None:
        fields[name] = value
