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
    default_message: str = "Erro interno do servidor"

    def __init__(self, message: str | None = None, detail: Any = None) -> None:
        self.message = message or self.default_message
        self.detail = detail  # optional extra context (dict, list, etc.)
        super().__init__(self.message)


# ── 400 ───────────────────────────────────────────────────────────────────────

class ValidationError(AcollyaException):
    status_code = 400
    default_message = "Dados de requisição inválidos"


# ── 401 ───────────────────────────────────────────────────────────────────────

class AuthenticationError(AcollyaException):
    status_code = 401
    default_message = "Autenticação necessária"


class TokenExpiredError(AuthenticationError):
    default_message = "Token expirado"


class InvalidTokenError(AuthenticationError):
    default_message = "Token inválido"


# ── 402 ───────────────────────────────────────────────────────────────────────

class PaymentRequiredError(AcollyaException):
    status_code = 402
    default_message = "É necessário ter uma assinatura para acessar este recurso"


class TrialExpiredError(PaymentRequiredError):
    default_message = "Seu período de avaliação gratuita encerrou. Assine para continuar."


class PremiumRequiredError(PaymentRequiredError):
    default_message = "Este recurso requer uma assinatura premium"


# ── 403 ───────────────────────────────────────────────────────────────────────

class AuthorizationError(AcollyaException):
    status_code = 403
    default_message = "Você não tem permissão para realizar esta ação"


class ConsentRequiredError(AcollyaException):
    """LGPD Art. 11 — tratamento de dado sensível bloqueado até o consentimento granular."""
    status_code = 403
    default_message = (
        "Para continuar, precisamos do seu consentimento para o tratamento de "
        "dados de saúde emocional. Conclua o aceite nos Termos do app."
    )


# ── 404 ───────────────────────────────────────────────────────────────────────

class NotFoundError(AcollyaException):
    status_code = 404
    default_message = "Recurso não encontrado"


# ── 409 ───────────────────────────────────────────────────────────────────────

class ConflictError(AcollyaException):
    status_code = 409
    default_message = "Recurso já existe"


# ── 429 ───────────────────────────────────────────────────────────────────────

class RateLimitError(AcollyaException):
    """Raised when the user hits the chat message rate limit."""

    status_code = 429
    default_message = "Limite de requisições atingido. Tente novamente mais tarde."

    def __init__(
        self,
        message: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after  # seconds until window resets
