"""
Alembic environment configuration.

Usage:
  # Run locally against dev DB:
  alembic upgrade head

  # Run against a specific stage (reads .env.{stage}):
  STAGE=prod alembic upgrade head

  # Generate a new migration:
  alembic revision --autogenerate -m "add push tokens"
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.database import Base

# Import all models so Alembic can detect them for --autogenerate
from app.models import (  # noqa: F401
    user,
    subscription,
    mood_checkin,
    journal_entry,
    chat_session,
    chat_message,
    appointment,
    program_progress,
    program,
    therapist,
    user_session,
)

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Use sync URL from settings (Alembic doesn't support async engines)."""
    return settings.sync_database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
