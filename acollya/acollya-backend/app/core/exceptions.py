"""
Custom exception hierarchy for Acollya API.

All domain exceptions inherit from AcollyaException so that a single
exception_handler registration in main.py can convert them to the correct
HTTP response.

HTTP status mapping:
  400  ValidationError    - malformed request data
  401  AuthenticationError - missing or invalid token
  402  PaymentRequiredError - subscription required (trial expired / premium feature)
  403  AuthorizationError  - authenticated but insufficient permissions
  404  NotFoundError       - resource does not exist
  409  ConflictError       - duplicate resource (email already registered, etc.)
  429  RateLimitError      - too many requests
  500  (base AcollyaException without override) - internal error
"""
from typing import Any


class AcollyaException(Exception):
    """Base exception. Catches anything not covered by a subclass."""

    status_code: int = 500
    default_message: str = "Internal server error"

    def __init__(self, message: str | None = None, detail: Any = None) -> None:
        self.message = message or self.default_message
        self.detail = detail  # optional extra context (dict, list, etc.)
        super().__init__(self.message)


# ── 400 ───────────────────────────────────────────────────────────────────────

class ValidationError(AcollyaException):
    status_code = 400
    default_message = "Invalid request data"


# ── 401 ───────────────────────────────────────────────────────────────────────

class AuthenticationError(AcollyaException):
    status_code = 401
    default_message = "Authentication required"


class TokenExpiredError(AuthenticationError):
    default_message = "Token has expired"


class InvalidTokenError(AuthenticationError):
    default_message = "Invalid token"


# ── 402 ───────────────────────────────────────────────────────────────────────

class PaymentRequiredError(AcollyaException):
    status_code = 402
    default_message = "A subscription is required to access this feature"


class TrialExpiredError(PaymentRequiredError):
    default_message = "Your free trial has ended. Subscribe to continue."


class PremiumRequiredError(PaymentRequiredError):
    default_message = "This feature requires a premium subscription"


# ── 403 ───────────────────────────────────────────────────────────────────────

class AuthorizationError(AcollyaException):
    status_code = 403
    default_message = "You do not have permission to perform this action"


# ── 404 ───────────────────────────────────────────────────────────────────────

class NotFoundError(AcollyaException):
    status_code = 404
    default_message = "Resource not found"


# ── 409 ───────────────────────────────────────────────────────────────────────

class ConflictError(AcollyaException):
    status_code = 409
    default_message = "Resource already exists"


# ── 429 ───────────────────────────────────────────────────────────────────────

class RateLimitError(AcollyaException):
    """Raised when the user hits the chat message rate limit."""

    status_code = 429
    default_message = "Rate limit exceeded. Try again later."

    def __init__(
        self,
        message: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after  # seconds until window resets
