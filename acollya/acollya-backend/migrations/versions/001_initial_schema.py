"""Initial schema — migrated from Supabase PostgreSQL

Revision ID: 001
Revises:
Create Date: 2026-03-29

Changes from original Supabase schema:
  - Removed auth.users dependency (Supabase-specific)
  - Added password_hash, google_id for custom auth
  - Added push_token_fcm, push_token_apns for mobile notifications
  - Added chat_sessions table (referenced in existing web app but not in schema.sql)
  - Added user_sessions table (from migration file 20240122)
  - Added ai_response_cache table with pgvector for embedding similarity cache
  - Added revenue_cat_id for RevenueCat IAP integration
  - Removed Supabase RLS policies (security handled via JWT in FastAPI)
  - All updated_at triggers migrated to SQLAlchemy event listeners
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # pgvector

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),  # NULL for OAuth users
        sa.Column("google_id", sa.Text(), nullable=True, unique=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("plan_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trial_ends_at", sa.TIMESTAMP(timezone=True), nullable=True,
                  server_default=sa.text("NOW() + INTERVAL '14 days'")),
        sa.Column("subscription_status", sa.Text(), nullable=True, server_default="'trialing'"),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True, unique=True),
        sa.Column("revenue_cat_id", sa.Text(), nullable=True, unique=True),
        sa.Column("push_token_fcm", sa.Text(), nullable=True),    # Android
        sa.Column("push_token_apns", sa.Text(), nullable=True),   # iOS
        sa.Column("terms_accepted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("terms_accepted_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_stripe_customer_id", "users", ["stripe_customer_id"])
    op.create_index("idx_users_google_id", "users", ["google_id"])

    # ── subscriptions ─────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default="'stripe'"),  # stripe, apple, google
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True, unique=True),
        sa.Column("stripe_price_id", sa.Text(), nullable=True),
        sa.Column("revenue_cat_entitlement", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("current_period_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_subscriptions_user_id", "subscriptions", ["user_id"])

    # ── mood_checkins ─────────────────────────────────────────────────────────
    op.create_table(
        "mood_checkins",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mood", sa.Text(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("ai_insight", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("intensity >= 1 AND intensity <= 5", name="ck_mood_intensity"),
    )
    op.create_index("idx_mood_checkins_user_id", "mood_checkins", ["user_id"])
    op.create_index("idx_mood_checkins_created_at", "mood_checkins", ["created_at"])

    # ── journal_entries ───────────────────────────────────────────────────────
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ai_reflection", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_journal_entries_user_id", "journal_entries", ["user_id"])
    op.create_index("idx_journal_entries_created_at", "journal_entries", ["created_at"])

    # ── chat_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_chat_sessions_user_id", "chat_sessions", ["user_id"])

    # ── chat_messages ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.UUID(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_message_role"),
    )
    op.create_index("idx_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("idx_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("idx_chat_messages_created_at", "chat_messages", ["created_at"])

    # ── appointments ──────────────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("therapist_id", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("payment_status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("meeting_link", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status IN ('pending', 'confirmed', 'completed', 'cancelled')", name="ck_appointment_status"),
        sa.CheckConstraint("payment_status IN ('pending', 'paid', 'refunded')", name="ck_appointment_payment_status"),
    )
    op.create_index("idx_appointments_user_id", "appointments", ["user_id"])
    op.create_index("idx_appointments_date", "appointments", ["date"])

    # ── program_progress ──────────────────────────────────────────────────────
    op.create_table(
        "program_progress",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("chapter_id", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "program_id", "chapter_id", name="uq_program_progress"),
    )
    op.create_index("idx_program_progress_user_id", "program_progress", ["user_id"])

    # ── user_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_type", sa.Text(), nullable=True),
        sa.Column("login_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("logout_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("device_type", sa.Text(), nullable=True),  # ios, android, web
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_user_sessions_user_id", "user_sessions", ["user_id"])

    # ── ai_response_cache (pgvector) ──────────────────────────────────────────
    # Stores embedding vectors for semantic similarity caching of AI responses.
    # Vector dimension 1536 = OpenAI text-embedding-3-small output size.
    op.create_table(
        "ai_response_cache",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("query_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW() + INTERVAL '30 days'")),
    )
    # Add vector column separately (requires pgvector extension to be loaded first)
    op.execute("ALTER TABLE ai_response_cache ADD COLUMN query_embedding vector(1536)")
    # IVFFlat index for fast approximate nearest neighbor search
    op.execute(
        "CREATE INDEX idx_ai_cache_embedding ON ai_response_cache "
        "USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.create_index("idx_ai_cache_query_hash", "ai_response_cache", ["query_hash"])
    op.create_index("idx_ai_cache_expires_at", "ai_response_cache", ["expires_at"])

    # ── updated_at trigger function ───────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    for table in ["users", "subscriptions", "journal_entries", "chat_sessions",
                  "appointments", "program_progress"]:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    for table in ["users", "subscriptions", "journal_entries", "chat_sessions",
                  "appointments", "program_progress"]:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.drop_table("ai_response_cache")
    op.drop_table("user_sessions")
    op.drop_table("program_progress")
    op.drop_table("appointments")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("journal_entries")
    op.drop_table("mood_checkins")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
