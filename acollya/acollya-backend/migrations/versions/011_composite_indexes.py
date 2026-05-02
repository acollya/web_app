"""Composite indexes for common query patterns.

Adds composite (user_id, created_at DESC/ASC) indexes that serve both the
WHERE user_id = ? filter and the ORDER BY created_at sort in a single index
scan — eliminating the separate sort step on paginated history queries.

Additional:
  - (session_id, created_at ASC) for in-session message loading (chronological)
  - (user_id, category) on user_persona_facts speeds up the dedup similarity
    search that filters by user_id AND category before the vector scan.

The existing single-column indexes (user_id, created_at) are kept because
they may still be chosen by the planner for queries that don't need the sort,
and dropping them would require coordinating with services that rely on them.

Note: CONCURRENTLY is used to avoid locking the table during index creation.
Requires running alembic with --isolation-level=AUTOCOMMIT or equivalent.

Revision ID: 011
Revises: 010
"""
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # chat_messages: user history pagination (DESC) + in-session loading (ASC)
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_user_created "
        "ON chat_messages (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_session_created "
        "ON chat_messages (session_id, created_at ASC)"
    )

    # journal_entries: paginated journal list per user
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_user_created "
        "ON journal_entries (user_id, created_at DESC)"
    )

    # mood_checkins: paginated mood history per user
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mood_checkins_user_created "
        "ON mood_checkins (user_id, created_at DESC)"
    )

    # user_persona_facts: dedup search filters by (user_id, category) before vector scan
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_persona_facts_user_category "
        "ON user_persona_facts (user_id, category)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chat_messages_user_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chat_messages_session_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_journal_entries_user_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_mood_checkins_user_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_persona_facts_user_category")
