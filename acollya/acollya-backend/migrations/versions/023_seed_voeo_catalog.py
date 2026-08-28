"""Seed do Catálogo de Produtos Digitais — Voeo (50 programas).

Fonte da verdade: content/catalog_voeo.json (revisado pelo Kadu em 2026-08-27;
textos de resumo/descrição serão refinados depois com as skills de copy).

Estratégia:
  - Os 5 programas originais (migration 004) viram os 5 programas CENTRAIS do
    catálogo via UPDATE in-place — preserva UUIDs, chapters (26) e program_progress.
  - Os demais 45 são INSERTs novos (UUID + slug), sem capítulos (conteúdo virá depois).
  - Cada programa gera 1 chunk em clinical_knowledge (category='catalogo_programas',
    source='catalogo_voeo') — o RAG do chat passa a conhecer o catálogo.
  - Embeddings ficam NULL (inclusive os 5 atualizados — texto mudou) e são gerados
    pelos jobs idempotentes embed_pending_programs() / embed_all_pending().

Revision ID: 023
Revises: 022
"""
import json
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "content" / "catalog_voeo.json"

# Programas da migration 004 → programa central equivalente do catálogo
_LEGACY_TO_CENTRAL = {
    "mindfulness-iniciantes": "presenca-21-dias",
    "gestao-ansiedade": "ansiedade-sob-controle",
    "autoestima-confianca": "meu-valor",
    "relacionamentos-saudaveis": "falando-a-mesma-lingua",
    "sono-reparador": "reaprendendo-a-dormir",
}

_PLAN_LABEL = {1: "Incluso nos planos Cuidado Essencial e Cuidado Completo",
               2: "Incluso no plano Cuidado Completo"}


def _chunk_text(p: dict) -> str:
    """Texto do chunk de conhecimento sobre o programa (para RAG do chat)."""
    plan = _PLAN_LABEL.get(p["min_plan_code"], "Disponível por upgrade de plano ou compra avulsa")
    price = ""
    if p.get("price_min_brl"):
        pmin, pmax = p["price_min_brl"], p["price_max_brl"]
        price = f"Preço avulso: R$ {pmin}" + (f" a R$ {pmax}" if pmax and pmax != pmin else "")
    parts = [
        f"Programa do Acollya: {p['title']}",
        f"Formato: {p['duration_label']}. Nível: {p['difficulty']}.",
        f"Público específico: {p['audience']}." if p.get("audience") else "",
        f"{plan}. {price}".strip(),
        p["description"],
        p["about"],
    ]
    return "\n".join(x for x in parts if x)


def upgrade() -> None:
    catalog = json.loads(_CATALOG_PATH.read_text())
    programs = catalog["programs"]
    by_slug = {p["slug"]: p for p in programs}
    conn = op.get_bind()

    update_sql = sa.text("""
        UPDATE programs SET
            slug = :slug, title = :title, description = :description, about = :about,
            category = :category, duration_days = :duration_days,
            duration_label = :duration_label, format = :format,
            difficulty = :difficulty, audience = :audience,
            min_plan_code = :min_plan_code, price_min_brl = :price_min_brl,
            price_max_brl = :price_max_brl, sort_order = :sort_order,
            embedding = NULL, is_active = TRUE
        WHERE slug = :legacy_slug
    """)
    insert_sql = sa.text("""
        INSERT INTO programs (id, slug, title, description, about, category,
            duration_days, duration_label, format, difficulty, audience,
            min_plan_code, price_min_brl, price_max_brl, is_premium, is_active,
            sort_order)
        VALUES (gen_random_uuid(), :slug, :title, :description, :about, :category,
            :duration_days, :duration_label, :format, :difficulty, :audience,
            :min_plan_code, :price_min_brl, :price_max_brl, TRUE, TRUE, :sort_order)
        ON CONFLICT (slug) DO NOTHING
    """)

    central_slugs = set(_LEGACY_TO_CENTRAL.values())
    for legacy_slug, central_slug in _LEGACY_TO_CENTRAL.items():
        p = by_slug[central_slug]
        conn.execute(update_sql, {**_params(p), "legacy_slug": legacy_slug})

    for p in programs:
        if p["slug"] in central_slugs:
            continue
        conn.execute(insert_sql, _params(p))

    # ── Base de conhecimento (RAG) — 1 chunk por programa ────────────────────
    conn.execute(sa.text(
        "DELETE FROM clinical_knowledge WHERE source = 'catalogo_voeo'"
    ))
    kb_sql = sa.text("""
        INSERT INTO clinical_knowledge (category, title, chunk_text, source)
        VALUES ('catalogo_programas', :title, :chunk_text, 'catalogo_voeo')
    """)
    for p in programs:
        conn.execute(kb_sql, {"title": p["title"], "chunk_text": _chunk_text(p)})


def _params(p: dict) -> dict:
    return {
        "slug": p["slug"],
        "title": p["title"],
        "description": p["description"],
        "about": p["about"],
        "category": p["category"],
        "duration_days": p["duration_days"],
        "duration_label": p["duration_label"],
        "format": p["format"],
        "difficulty": p["difficulty"],
        "audience": p.get("audience"),
        "min_plan_code": p.get("min_plan_code"),
        "price_min_brl": p.get("price_min_brl"),
        "price_max_brl": p.get("price_max_brl"),
        "sort_order": p["sort_order"],
    }


def downgrade() -> None:
    catalog = json.loads(_CATALOG_PATH.read_text())
    central_slugs = set(_LEGACY_TO_CENTRAL.values())
    conn = op.get_bind()

    conn.execute(sa.text("DELETE FROM clinical_knowledge WHERE source = 'catalogo_voeo'"))

    # Remove os inseridos (mantém os 5 centrais, que eram os programas originais)
    other_slugs = [p["slug"] for p in catalog["programs"] if p["slug"] not in central_slugs]
    conn.execute(
        sa.text("DELETE FROM programs WHERE slug = ANY(:slugs)"),
        {"slugs": other_slugs},
    )

    # Reverte os 5 centrais para a identidade da migration 004
    legacy = {
        "presenca-21-dias": ("mindfulness-iniciantes", "Mindfulness para Iniciantes",
                             "Aprenda tecnicas de atencao plena para reduzir o estresse e aumentar o bem-estar no dia a dia.",
                             "mindfulness", 7, "beginner", 0),
        "ansiedade-sob-controle": ("gestao-ansiedade", "Gestao de Ansiedade",
                                   "Ferramentas praticas baseadas em TCC para identificar e lidar com a ansiedade do cotidiano.",
                                   "anxiety", 10, "intermediate", 1),
        "meu-valor": ("autoestima-confianca", "Autoestima e Confianca",
                      "Uma jornada para reconhecer seu valor, superar a autocritica e construir uma imagem positiva de si mesmo.",
                      "self-esteem", 14, "intermediate", 2),
        "falando-a-mesma-lingua": ("relacionamentos-saudaveis", "Relacionamentos Saudaveis",
                                   "Desenvolva habilidades de comunicacao, limites saudaveis e conexoes mais autenticas.",
                                   "relationships", 10, "intermediate", 3),
        "reaprendendo-a-dormir": ("sono-reparador", "Sono Reparador",
                                  "Tecnicas de higiene do sono e relaxamento para melhorar a qualidade do seu descanso.",
                                  "sleep", 7, "beginner", 4),
    }
    revert_sql = sa.text("""
        UPDATE programs SET slug=:old_slug, title=:title, description=:description,
            about=NULL, category=:category, duration_days=:days,
            duration_label=NULL, format=NULL, difficulty=:difficulty, audience=NULL,
            min_plan_code=NULL, price_min_brl=NULL, price_max_brl=NULL,
            sort_order=:sort, embedding=NULL
        WHERE slug=:new_slug
    """)
    for new_slug, (old_slug, title, desc, cat, days, diff, sort) in legacy.items():
        conn.execute(revert_sql, {
            "new_slug": new_slug, "old_slug": old_slug, "title": title,
            "description": desc, "category": cat, "days": days,
            "difficulty": diff, "sort": sort,
        })
