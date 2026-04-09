"""
Application configuration via environment variables.

In Lambda: env vars are set by CDK (ApiStack shared_env dict).
In local dev: loaded from .env file via python-dotenv.

AWS Secrets Manager values are loaded lazily at first use (cached in memory
for the Lambda container lifetime, refreshed on cold start).
"""
import json
import logging
from functools import cached_property
from typing import Optional

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core ──────────────────────────────────────────────────────────────────
    stage: str = "dev"
    log_level: str = "INFO"
    aws_account_id: str = ""
    aws_region: str = "sa-east-1"

    # ── Database ──────────────────────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "acollya"
    db_secret_arn: Optional[str] = None  # Secrets Manager ARN for user/pass
    # Local dev only (not used in Lambda):
    db_user: str = "acollya_admin"
    db_password: str = "localdev"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_tls: bool = False  # ElastiCache standalone cluster does not support TLS
    redis_password: Optional[str] = None

    # ── Storage ───────────────────────────────────────────────────────────────
    media_bucket: str = "acollya-media-local"

    # ── Secrets Manager ARNs (resolved lazily) ────────────────────────────────
    jwt_secret_arn: str = "acollya/dev/jwt"
    openai_secret_arn: str = "acollya/dev/openai"
    stripe_secret_arn: str = "acollya/dev/stripe"

    # ── Local dev overrides (used when stage=dev and no Secrets Manager) ──────
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    # Comma-separated list of allowed Google OAuth client IDs
    # e.g. "123.apps.googleusercontent.com,456.apps.googleusercontent.com"
    google_client_ids: str = ""

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_insight_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_secret_arn: str = "acollya/dev/anthropic"
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-haiku-4-5-20251001"
    anthropic_insight_model: str = "claude-haiku-4-5-20251001"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_monthly_price_id: str = ""
    stripe_annual_price_id: str = ""

    # ── App Config ────────────────────────────────────────────────────────────
    trial_days: int = 14
    free_chat_messages_per_day: int = 20
    premium_chat_messages_per_day: int = 9999

    # ── CORS ──────────────────────────────────────────────────────────────────
    @property
    def cors_origins(self) -> list[str]:
        if self.stage == "prod":
            return [
                "https://acollya.com.br",
                "https://www.acollya.com.br",
                "https://app.acollya.com.br",
            ]
        return ["*"]

    # ── Database URL ──────────────────────────────────────────────────────────
    @cached_property
    def database_url(self) -> str:
        """Async SQLAlchemy URL. Resolves credentials from Secrets Manager in Lambda."""
        user, password = self._get_db_credentials()
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @cached_property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic migrations."""
        user, password = self._get_db_credentials()
        return (
            f"postgresql+psycopg2://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def _get_db_credentials(self) -> tuple[str, str]:
        """Fetch DB credentials from Secrets Manager (Lambda) or env vars (local)."""
        if self.db_secret_arn and self.stage != "dev":
            secret = self._get_secret(self.db_secret_arn)
            return secret["username"], secret["password"]
        return self.db_user, self.db_password

    @cached_property
    def jwt_config(self) -> dict:
        """JWT configuration from Secrets Manager or env vars."""
        if self.jwt_secret_arn and self.stage != "dev":
            return self._get_secret(self.jwt_secret_arn)
        client_ids = [c.strip() for c in self.google_client_ids.split(",") if c.strip()]
        return {
            "private_key": self.jwt_private_key,
            "public_key": self.jwt_public_key,
            "algorithm": self.jwt_algorithm,
            "access_token_expire_minutes": self.access_token_expire_minutes,
            "refresh_token_expire_days": self.refresh_token_expire_days,
            "google_client_ids": client_ids,
        }

    @cached_property
    def openai_config(self) -> dict:
        """OpenAI config from Secrets Manager or env vars."""
        if self.openai_secret_arn and self.stage != "dev":
            secret = self._get_secret(self.openai_secret_arn)
            # Secrets Manager may not have insight_model — fall back to default
            secret.setdefault("insight_model", self.openai_insight_model)
            return secret
        return {
            "api_key": self.openai_api_key,
            "chat_model": self.openai_chat_model,
            "insight_model": self.openai_insight_model,
            "embedding_model": self.openai_embedding_model,
        }

    @cached_property
    def anthropic_config(self) -> dict:
        """Anthropic config from Secrets Manager or env vars."""
        if self.anthropic_secret_arn and self.stage != "dev":
            secret = self._get_secret(self.anthropic_secret_arn)
            secret.setdefault("chat_model", self.anthropic_chat_model)
            secret.setdefault("insight_model", self.anthropic_insight_model)
            return secret
        return {
            "api_key": self.anthropic_api_key,
            "chat_model": self.anthropic_chat_model,
            "insight_model": self.anthropic_insight_model,
        }

    @cached_property
    def stripe_config(self) -> dict:
        """Stripe config from Secrets Manager or env vars."""
        if self.stripe_secret_arn and self.stage != "dev":
            return self._get_secret(self.stripe_secret_arn)
        return {
            "secret_key": self.stripe_secret_key,
            "webhook_secret": self.stripe_webhook_secret,
            "monthly_price_id": self.stripe_monthly_price_id,
            "annual_price_id": self.stripe_annual_price_id,
        }

    @staticmethod
    def _get_secret(secret_name: str) -> dict:
        """Fetch and parse a JSON secret from AWS Secrets Manager."""
        try:
            client = boto3.client("secretsmanager", region_name="sa-east-1")
            response = client.get_secret_value(SecretId=secret_name)
            return json.loads(response["SecretString"])
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_name}: {e}")
            raise


settings = Settings()
