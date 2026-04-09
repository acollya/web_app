"""Remove ON DELETE CASCADE; add anonymization fields to users

Revision ID: 008
Revises: 007
Create Date: 2026-04-08

Motivação
---------
Os embeddings armazenados em chat_messages, journal_entries, mood_checkins e
user_persona_facts são ativos valiosos para fine-tuning de SLMs. O CASCADE
anterior apagava todos esses dados junto com o usuário, inviabilizando o reuso.

Nova estratégia (LGPD Art. 18):
  - Usuário solicita exclusão → PII é apagado/substituído (anonimização)
  - Linha do usuário permanece com is_anonymized=True e anonymized_at
  - Registros de conteúdo (mensagens, diário, humor, persona) permanecem
    linkados ao usuário anonimizado — sem PII, prontos para fine-tuning
  - Nenhuma FK com ON DELETE CASCADE: sem risco de perda acidental de dados
    por um hard DELETE em nível de banco

Tabelas alteradas (FK → sem ON DELETE)
---------------------------------------
  subscriptions        .user_id → users.id
  mood_checkins        .user_id → users.id
  journal_entries      .user_id → users.id
  chat_sessions        .user_id → users.id
  chat_messages        .user_id → users.id
  chat_messages        .session_id → chat_sessions.id
  appointments         .user_id → users.id
  program_progress     .user_id → users.id
  user_sessions        .user_id → users.id
  user_persona_facts   .user_id → users.id
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ── Revision ──────────────────────────────────────────────────────────────────

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Mapa de FKs a migrar ──────────────────────────────────────────────────────
# (constraint_name, table, local_col, ref_table, ref_col)

_FK_MAP = [
    ("subscriptions_user_id_fkey",      "subscriptions",      "user_id",    "users",         "id"),
    ("mood_checkins_user_id_fkey",      "mood_checkins",      "user_id",    "users",         "id"),
    ("journal_entries_user_id_fkey",    "journal_entries",    "user_id",    "users",         "id"),
    ("chat_sessions_user_id_fkey",      "chat_sessions",      "user_id",    "users",         "id"),
    ("chat_messages_user_id_fkey",      "chat_messages",      "user_id",    "users",         "id"),
    ("chat_messages_session_id_fkey",   "chat_messages",      "session_id", "chat_sessions", "id"),
    ("appointments_user_id_fkey",       "appointments",       "user_id",    "users",         "id"),
    ("program_progress_user_id_fkey",   "program_progress",   "user_id",    "users",         "id"),
    ("user_sessions_user_id_fkey",      "user_sessions",      "user_id",    "users",         "id"),
    ("user_persona_facts_user_id_fkey", "user_persona_facts", "user_id",    "users",         "id"),
]

# ── Upgrade ───────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # 1. Campos de anonimização na tabela users
    op.add_column(
        "users",
        sa.Column("is_anonymized", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Substitui cada FK com CASCADE por uma sem ON DELETE (comportamento RESTRICT)
    for name, table, local_col, ref_table, ref_col in _FK_MAP:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name,           # mantém o mesmo nome para consistência
            table,
            ref_table,
            [local_col],
            [ref_col],
            # sem ondelete → banco usa RESTRICT (padrão); bloqueia hard DELETE acidental
        )


# ── Downgrade ─────────────────────────────────────────────────────────────────


def downgrade() -> None:
    # Restaura FKs com CASCADE
    for name, table, local_col, ref_table, ref_col in reversed(_FK_MAP):
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name,
            table,
            ref_table,
            [local_col],
            [ref_col],
            ondelete="CASCADE",
        )

    op.drop_column("users", "anonymized_at")
    op.drop_column("users", "is_anonymized")
