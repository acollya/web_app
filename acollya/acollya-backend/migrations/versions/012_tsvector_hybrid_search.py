"""Add tsvector columns for BM25 lexical search (hybrid search foundation).

Adds generated tsvector columns to chat_messages and journal_entries so the
RAG service can combine BM25 (full-text) and vector (semantic) scores using
Reciprocal Rank Fusion (RRF), improving recall on keyword-heavy queries.

Why BM25 + vector:
  - Vector search excels at semantic similarity ("sinto que não consigo respirar"
    matches "ansiedade") but misses exact-keyword queries.
  - BM25 excels at exact terms ("CBT", "Terapia Cognitivo-Comportamental") but
    has no semantic awareness.
  - RRF fusion with k=60: combined_score = 1/(k + rank_bm25) + 1/(k + rank_vec)
    consistently outperforms either alone on mixed query types.

tsvector configuration:
  - 'portuguese' stemmer: handles "ansiedade", "ansioso", "ansiosa" → same token.
  - STORED: computed once at write time, no recomputation on SELECT.
  - GIN index: fast @@ and ts_rank_cd operations.

Tables:
  chat_messages   → ts_content = to_tsvector('portuguese', content)
  journal_entries → ts_content = to_tsvector('portuguese', coalesce(title,'') || ' ' || content)

Revision ID: 012
Revises: 011
"""
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # chat_messages: generated tsvector on content
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD COLUMN ts_content tsvector
        GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED
        """
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_ts_content "
        "ON chat_messages USING gin(ts_content)"
    )

    # journal_entries: generated tsvector on title + content
    op.execute(
        """
        ALTER TABLE journal_entries
        ADD COLUMN ts_content tsvector
        GENERATED ALWAYS AS (
            to_tsvector('portuguese', coalesce(title, '') || ' ' || content)
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_ts_content "
        "ON journal_entries USING gin(ts_content)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_journal_entries_ts_content")
    op.execute("ALTER TABLE journal_entries DROP COLUMN IF EXISTS ts_content")

    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chat_messages_ts_content")
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS ts_content")
