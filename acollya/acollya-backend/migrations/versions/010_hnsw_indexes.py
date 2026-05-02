"""Replace IVFFlat with HNSW indexes for all embedding columns.

HNSW advantages over IVFFlat:
- Superior recall (~98% vs ~90%) without per-session probes tuning
- Works well on small per-user datasets (IVFFlat degrades below lists*3 rows)
- No periodic REINDEX required as data grows
- Consistent latency regardless of cluster distribution

Memory note: each HNSW index uses ~2MB per 10k vectors of 1536 dims.
With db.t3.micro (1GB RAM) this is acceptable up to ~100k vectors per table.

Revision ID: 010
Revises: 009
"""
from alembic import op
from sqlalchemy import text

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

_TABLES = [
    "chat_messages",
    "journal_entries",
    "mood_checkins",
    "user_persona_facts",
]

_OLD_INDEX_NAMES = {
    "chat_messages":    "ix_chat_messages_embedding",
    "journal_entries":  "ix_journal_entries_embedding",
    "mood_checkins":    "ix_mood_checkins_embedding",
    "user_persona_facts": "ix_user_persona_facts_embedding",
}

_NEW_INDEX_NAMES = {
    "chat_messages":    "ix_chat_messages_embedding_hnsw",
    "journal_entries":  "ix_journal_entries_embedding_hnsw",
    "mood_checkins":    "ix_mood_checkins_embedding_hnsw",
    "user_persona_facts": "ix_user_persona_facts_embedding_hnsw",
}


def upgrade() -> None:
    # CONCURRENTLY operations cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        for table in _TABLES:
            old_idx = _OLD_INDEX_NAMES[table]
            new_idx = _NEW_INDEX_NAMES[table]
            op.execute(text(f"DROP INDEX CONCURRENTLY IF EXISTS {old_idx}"))
            op.execute(text(
                f"CREATE INDEX CONCURRENTLY {new_idx} "
                f"ON {table} USING hnsw (embedding vector_cosine_ops) "
                f"WITH (m = 16, ef_construction = 64)"
            ))


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for table in _TABLES:
            old_idx = _OLD_INDEX_NAMES[table]
            new_idx = _NEW_INDEX_NAMES[table]
            op.execute(text(f"DROP INDEX CONCURRENTLY IF EXISTS {new_idx}"))
            op.execute(text(
                f"CREATE INDEX CONCURRENTLY {old_idx} "
                f"ON {table} USING ivfflat (embedding vector_cosine_ops) "
                f"WITH (lists = 50)"
            ))
