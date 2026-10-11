"""Domain errors mapped to the error catalogue (spec Section 33)."""
from typing import Any

# code -> (HTTP status, retryable)
CATALOGUE: dict[str, tuple[int, bool]] = {
    "VALIDATION_FAILED": (400, False),
    "STATE_MISMATCH": (400, False),
    "CURRENCY_REQUIRED": (400, False),
    "RULE_INVALID": (400, False),
    "AUTHENTICATION_REQUIRED": (401, False),
    "INVALID_CREDENTIALS": (401, False),
    "AUTHORIZATION_DENIED": (403, False),
    "ORG_NOT_SELECTED": (403, False),
    "INVITATION_EMAIL_MISMATCH": (403, False),
    "GOOGLE_ACCOUNT_NOT_LINKED": (403, False),
    "CONSENT_REQUIRED": (403, False),
    "ON_BREAK": (403, False),
    "ON_APPROVED_LEAVE": (403, False),
    "NOT_FOUND": (404, False),
    "VERSION_CONFLICT": (409, False),
    "IDEMPOTENCY_KEY_REUSED": (409, False),
    "SLUG_TAKEN": (409, False),
    "EMAIL_IN_USE": (409, False),
    "POLICY_VERSION_OUTDATED": (409, False),
    "SESSION_CLOSED": (409, False),
    "NO_OPEN_SESSION": (409, False),
    "BREAK_ALREADY_ACTIVE": (409, False),
    "ALREADY_DECIDED": (409, False),
    "STREAM_NOT_LIVE": (409, False),
    "LEAVE_OVERLAP": (409, False),
    "TIME_OVERLAPS_SESSION": (409, False),
    "ALREADY_WON": (409, False),
    "INVOICE_NUMBER_TAKEN": (409, False),
    "ALREADY_RESOLVED": (409, False),
    "INVITATION_INVALID": (410, False),
    "RESET_TOKEN_EXPIRED": (410, False),
    "ONE_CEO_ONLY": (422, False),
    "CANNOT_DEACTIVATE_CEO": (422, False),
    "INSUFFICIENT_BALANCE": (422, False),
    "ASSIGNEE_NOT_MEMBER": (422, False),
    "INVALID_TRANSITION": (422, False),
    "LOST_REASON_REQUIRED": (422, False),
    "COMPANY_REQUIRED": (422, False),
    "OVERPAYMENT": (422, False),
    "SOURCE_NOT_ALLOWED": (422, False),
    "SUPPRESSED_CONTACT": (422, False),
    "MEMBER_DEACTIVATED": (423, False),
    "RATE_LIMITED": (429, True),
    "INTERNAL_ERROR": (500, True),
    "GOOGLE_NOT_CONFIGURED": (503, False),
    "MEDIA_UNAVAILABLE": (503, True),
}


class ApiError(Exception):
    """Raise from any layer; the exception handler renders the Section 19.1 error envelope."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        if code not in CATALOGUE:
            raise ValueError(f"Unknown error code {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers or {}
        self.status, self.retryable = CATALOGUE[code]


def not_found(what: str) -> ApiError:
    """Records in another company get the same response as missing records (Section 33)."""
    return ApiError("NOT_FOUND", f"{what} not found.")


def denied(message: str = "You do not have permission to do that.") -> ApiError:
    return ApiError("AUTHORIZATION_DENIED", message)


def invalid(message: str, fields: dict[str, str] | None = None) -> ApiError:
    return ApiError("VALIDATION_FAILED", message, {"fields": fields} if fields else None)


def version_conflict(current_version: int, message: str = "This record was changed by someone else. Reload and try again.") -> ApiError:
    return ApiError("VERSION_CONFLICT", message, {"current_version": current_version})
