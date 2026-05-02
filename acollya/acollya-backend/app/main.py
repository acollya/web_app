"""
Acollya FastAPI Application

Entry point for all HTTP requests routed through:
  - AWS Lambda + API Gateway (CRUD endpoints)
  - AWS Lambda Function URL (chat streaming)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.config import settings
from app.database import init_db
from app.core.exceptions import AcollyaException, RateLimitError
from app.services import chat_service, persona_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and teardown resources on Lambda cold start."""
    # Database connectivity check
    await init_db()

    # Redis client — shared across all requests in this Lambda container
    redis_url = (
        f"rediss://{settings.redis_host}:{settings.redis_port}"
        if settings.redis_tls
        else f"redis://{settings.redis_host}:{settings.redis_port}"
    )
    app.state.redis = Redis.from_url(
        redis_url,
        password=settings.redis_password,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    logger.info("Redis client initialised: %s", settings.redis_host)

    # Wire shared Redis into services that need it (avoids per-call connections)
    persona_service.configure_redis(app.state.redis)
    chat_service.configure_redis(app.state.redis)

    yield

    # Teardown — closes idle connections (called on Lambda container shutdown)
    await app.state.redis.aclose()


app = FastAPI(
    title="Acollya API",
    description="Mental health platform API — saude mental acessivel para todos",
    version="1.0.0",
    docs_url="/docs" if settings.stage != "prod" else None,
    redoc_url="/redoc" if settings.stage != "prod" else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(AcollyaException)
async def acollya_exception_handler(request: Request, exc: AcollyaException) -> JSONResponse:
    """Convert all domain exceptions to structured JSON responses."""
    headers = {}
    if isinstance(exc, RateLimitError) and exc.retry_after is not None:
        headers["Retry-After"] = str(exc.retry_after)

    body: dict = {"detail": exc.message}
    if exc.detail is not None:
        body["extra"] = exc.detail

    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic v2 validation errors — return 422 with field-level detail."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routes ────────────────────────────────────────────────────────────────────
# Imported here (not at module level) to avoid circular imports
from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "stage": settings.stage, "version": "1.0.0"}
