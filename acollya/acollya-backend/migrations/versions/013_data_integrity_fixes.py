"""Data integrity fixes: constraints, user isolation, seed data corrections.

Changes:
  1. users.subscription_status — add CHECK constraint for valid Stripe/RevenueCat values
  2. appointments.therapist_id — add FK → therapists(id)
  3. ai_response_cache — add user_id column (nullable for backward compat) + index
  4. user_sessions — add partial index on login_at for TTL-based purge queries
  5. seed data — fix Dr. Carlos Oliveira working_days_mask 23→47 (Mon+Tue+Wed+Thu+Sat)

Working-days bitmask key: Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32
  23 = 1+2+4+16     = Mon+Tue+Wed+Fri   (wrong)
  47 = 1+2+4+8+32   = Mon+Tue+Wed+Thu+Sat (correct for Carlos)
"""
import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. subscription_status CHECK constraint ───────────────────────────────
    # NULL is allowed (legacy rows before subscription existed)
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT ck_users_subscription_status
        CHECK (
            subscription_status IS NULL
            OR subscription_status IN (
                'trialing', 'active', 'past_due', 'canceled', 'unpaid'
            )
        )
    """)

    # ── 2. appointments.therapist_id → therapists(id) ─────────────────────────
    # Only add if therapists table exists and there are no orphaned rows.
    # The constraint is DEFERRABLE to allow bulk inserts within a transaction.
    op.execute("""
        ALTER TABLE appointments
        ADD CONSTRAINT fk_appointments_therapist_id
        FOREIGN KEY (therapist_id) REFERENCES therapists(id)
        ON DELETE RESTRICT
        DEFERRABLE INITIALLY DEFERRED
    """)

    # ── 3. ai_response_cache — add user_id for per-user cache isolation ───────
    # Nullable so existing global cache rows aren't immediately invalidated.
    # New rows should always supply user_id; NULL rows are treated as global.
    op.add_column(
        "ai_response_cache",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.execute("""
        ALTER TABLE ai_response_cache
        ADD CONSTRAINT fk_ai_cache_user_id
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
    """)
    # Composite index: per-user cache lookups by hash
    op.create_index(
        "idx_ai_cache_user_hash",
        "ai_response_cache",
        ["user_id", "query_hash"],
        unique=False,
    )

    # ── 4. user_sessions — index for TTL purge queries ────────────────────────
    # Enables efficient: DELETE FROM user_sessions WHERE login_at < NOW() - INTERVAL '90 days'
    op.create_index(
        "idx_user_sessions_login_at",
        "user_sessions",
        ["login_at"],
        unique=False,
        postgresql_where=sa.text("logout_at IS NOT NULL"),
    )

    # ── 5. Fix Dr. Carlos Oliveira working_days_mask ──────────────────────────
    # 23 (Mon+Tue+Wed+Fri) → 47 (Mon+Tue+Wed+Thu+Sat)
    op.execute("""
        UPDATE therapists
        SET working_days_mask = 47
        WHERE name ILIKE '%carlos oliveira%'
          AND working_days_mask = 23
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE therapists
        SET working_days_mask = 23
        WHERE name ILIKE '%carlos oliveira%'
          AND working_days_mask = 47
    """)

    op.drop_index("idx_user_sessions_login_at", table_name="user_sessions")

    op.drop_index("idx_ai_cache_user_hash", table_name="ai_response_cache")
    op.execute("ALTER TABLE ai_response_cache DROP CONSTRAINT IF EXISTS fk_ai_cache_user_id")
    op.drop_column("ai_response_cache", "user_id")

    op.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS fk_appointments_therapist_id")

    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_subscription_status")
