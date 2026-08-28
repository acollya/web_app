"""programs/chapters: id slug (text) → UUID; slug preservado em coluna própria.

Decisão (Kadu, 2026-08-01): IDs de tabela devem ser identificadores únicos
puros — semântica (slug legível como "ansiedade-2-1") vai para coluna `slug`.

Conversão in-place:
  programs.id  "gestao-ansiedade"  → id UUID + slug "gestao-ansiedade"
  chapters.id  "ansiedade-2-1"     → id UUID + slug "ansiedade-2-1"
  program_progress.program_id / chapter_id remapeados via join pelos slugs.

Índices preservados: idx_chapters_embedding (ivfflat) e ts_content não são
afetados (colunas intocadas). Índices sobre id/program_id são recriados.

Revision ID: 021
Revises: 020
"""
from typing import Sequence, Union

from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    -- ── 1. Novas colunas UUID + slug ──────────────────────────────────────────
    ALTER TABLE programs ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
    ALTER TABLE programs ADD COLUMN slug TEXT;
    UPDATE programs SET slug = id;
    ALTER TABLE programs ALTER COLUMN slug SET NOT NULL;

    ALTER TABLE chapters ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
    ALTER TABLE chapters ADD COLUMN slug TEXT;
    ALTER TABLE chapters ADD COLUMN new_program_id UUID;
    UPDATE chapters SET slug = id;
    UPDATE chapters c SET new_program_id = p.new_id FROM programs p WHERE c.program_id = p.id;
    ALTER TABLE chapters ALTER COLUMN slug SET NOT NULL;
    ALTER TABLE chapters ALTER COLUMN new_program_id SET NOT NULL;

    -- ── 2. Remap de program_progress (text → uuid) ────────────────────────────
    ALTER TABLE program_progress ADD COLUMN new_program_id UUID;
    ALTER TABLE program_progress ADD COLUMN new_chapter_id UUID;
    UPDATE program_progress pp SET new_program_id = p.new_id
      FROM programs p WHERE pp.program_id = p.id;
    UPDATE program_progress pp SET new_chapter_id = c.new_id
      FROM chapters c WHERE pp.chapter_id = c.id;
    -- Órfãos (referências a programas/capítulos inexistentes) são descartados
    DELETE FROM program_progress WHERE new_program_id IS NULL OR new_chapter_id IS NULL;

    -- ── 3. Troca de PKs / FKs ─────────────────────────────────────────────────
    ALTER TABLE chapters DROP CONSTRAINT chapters_program_id_fkey;
    ALTER TABLE chapters DROP CONSTRAINT chapters_pkey;
    ALTER TABLE programs DROP CONSTRAINT programs_pkey;

    ALTER TABLE programs DROP COLUMN id;
    ALTER TABLE programs RENAME COLUMN new_id TO id;
    ALTER TABLE programs ADD PRIMARY KEY (id);
    CREATE UNIQUE INDEX idx_programs_slug ON programs (slug);

    ALTER TABLE chapters DROP COLUMN id;
    ALTER TABLE chapters DROP COLUMN program_id;
    ALTER TABLE chapters RENAME COLUMN new_id TO id;
    ALTER TABLE chapters RENAME COLUMN new_program_id TO program_id;
    ALTER TABLE chapters ADD PRIMARY KEY (id);
    ALTER TABLE chapters ADD CONSTRAINT chapters_program_id_fkey
      FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE;
    CREATE UNIQUE INDEX idx_chapters_slug ON chapters (slug);
    CREATE INDEX idx_chapters_program_id ON chapters (program_id);
    CREATE INDEX idx_chapters_order ON chapters (program_id, "order");

    ALTER TABLE program_progress DROP CONSTRAINT uq_program_progress;
    ALTER TABLE program_progress DROP COLUMN program_id;
    ALTER TABLE program_progress DROP COLUMN chapter_id;
    ALTER TABLE program_progress RENAME COLUMN new_program_id TO program_id;
    ALTER TABLE program_progress RENAME COLUMN new_chapter_id TO chapter_id;
    ALTER TABLE program_progress ALTER COLUMN program_id SET NOT NULL;
    ALTER TABLE program_progress ALTER COLUMN chapter_id SET NOT NULL;
    ALTER TABLE program_progress ADD CONSTRAINT uq_program_progress
      UNIQUE (user_id, program_id, chapter_id);
    """)


def downgrade() -> None:
    op.execute("""
    -- Restaura os slugs como PKs de texto (reverso exato do upgrade)
    ALTER TABLE program_progress DROP CONSTRAINT uq_program_progress;
    ALTER TABLE program_progress ADD COLUMN old_program_id TEXT;
    ALTER TABLE program_progress ADD COLUMN old_chapter_id TEXT;
    UPDATE program_progress pp SET old_program_id = p.slug FROM programs p WHERE pp.program_id = p.id;
    UPDATE program_progress pp SET old_chapter_id = c.slug FROM chapters c WHERE pp.chapter_id = c.id;
    ALTER TABLE program_progress DROP COLUMN program_id;
    ALTER TABLE program_progress DROP COLUMN chapter_id;
    ALTER TABLE program_progress RENAME COLUMN old_program_id TO program_id;
    ALTER TABLE program_progress RENAME COLUMN old_chapter_id TO chapter_id;
    ALTER TABLE program_progress ALTER COLUMN program_id SET NOT NULL;
    ALTER TABLE program_progress ALTER COLUMN chapter_id SET NOT NULL;
    ALTER TABLE program_progress ADD CONSTRAINT uq_program_progress
      UNIQUE (user_id, program_id, chapter_id);

    ALTER TABLE chapters DROP CONSTRAINT chapters_program_id_fkey;
    ALTER TABLE chapters DROP CONSTRAINT chapters_pkey;
    DROP INDEX idx_chapters_slug;
    ALTER TABLE chapters ADD COLUMN old_program_id TEXT;
    UPDATE chapters c SET old_program_id = p.slug FROM programs p WHERE c.program_id = p.id;
    ALTER TABLE chapters DROP COLUMN id;
    ALTER TABLE chapters DROP COLUMN program_id;
    ALTER TABLE chapters RENAME COLUMN slug TO id;
    ALTER TABLE chapters RENAME COLUMN old_program_id TO program_id;
    ALTER TABLE chapters ADD PRIMARY KEY (id);
    ALTER TABLE chapters ALTER COLUMN program_id SET NOT NULL;

    ALTER TABLE programs DROP CONSTRAINT programs_pkey;
    DROP INDEX idx_programs_slug;
    ALTER TABLE programs DROP COLUMN id;
    ALTER TABLE programs RENAME COLUMN slug TO id;
    ALTER TABLE programs ADD PRIMARY KEY (id);

    ALTER TABLE chapters ADD CONSTRAINT chapters_program_id_fkey
      FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE;
    CREATE INDEX idx_chapters_program_id ON chapters (program_id);
    CREATE INDEX idx_chapters_order ON chapters (program_id, "order");
    """)
