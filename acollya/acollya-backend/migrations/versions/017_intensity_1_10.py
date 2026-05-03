"""Expand mood intensity constraint from 1–5 to 1–10.

Changes:
  1. mood_checkins — drop CHECK constraint ck_mood_intensity (intensity BETWEEN 1 AND 5)
  2. mood_checkins — add CHECK constraint ck_mood_intensity (intensity BETWEEN 1 AND 10)

Existing rows with intensity values 1–5 remain valid under the new constraint.
"""
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Drop the old 1–5 constraint ───────────────────────────────────────
    op.execute("""
        ALTER TABLE mood_checkins
        DROP CONSTRAINT IF EXISTS ck_mood_intensity
    """)

    # ── 2. Add the new 1–10 constraint ───────────────────────────────────────
    op.execute("""
        ALTER TABLE mood_checkins
        ADD CONSTRAINT ck_mood_intensity
        CHECK (intensity >= 1 AND intensity <= 10)
    """)


def downgrade() -> None:
    # ── Revert to 1–5 constraint ──────────────────────────────────────────────
    # WARNING: rows with intensity 6–10 will violate the restored constraint.
    # Ensure all such rows are updated or removed before running downgrade.
    op.execute("""
        ALTER TABLE mood_checkins
        DROP CONSTRAINT IF EXISTS ck_mood_intensity
    """)

    op.execute("""
        ALTER TABLE mood_checkins
        ADD CONSTRAINT ck_mood_intensity
        CHECK (intensity >= 1 AND intensity <= 5)
    """)
