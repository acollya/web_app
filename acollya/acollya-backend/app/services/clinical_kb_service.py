"""
clinical_kb_service — embedding ingestion for the clinical knowledge base
and program chapters.

Responsabilidades
-----------------
embed_all_pending()      — gera embeddings para todos os chunks de
                           clinical_knowledge que ainda não têm embedding
                           (idempotente). Pode ser chamado pós-migração,
                           em background tasks ou como job administrativo.

embed_pending_chapters() — gera embeddings para chapters com content_type='text'
                           que ainda não têm embedding (idempotente).

Design
------
Ambas as funções reutilizam _generate_embedding() do rag_service para
garantir consistência de modelo (text-embedding-3-small, 1536d) e
tratamento de erros. Erros em registros individuais são silenciados — o
registro simplesmente fica sem embedding e será reprocessado na próxima
execução.

Batch
-----
Processa até 100 registros por chamada para evitar timeouts em Lambda. Para
bases maiores, basta chamar a função várias vezes (ela é idempotente).
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical_knowledge import ClinicalKnowledge
from app.services.rag_service import _generate_embedding

logger = logging.getLogger(__name__)

# Limite por chamada — protege contra timeouts e custos descontrolados.
_BATCH_SIZE = 100


async def embed_all_pending(db: AsyncSession) -> int:
    """
    Gera embeddings para chunks de clinical_knowledge sem embedding.

    Retorna a quantidade de chunks efetivamente processados nesta chamada.
    Seguro para ser chamado múltiplas vezes (idempotente).
    """
    try:
        result = await db.execute(
            select(ClinicalKnowledge)
            .where(ClinicalKnowledge.embedding.is_(None))
            .limit(_BATCH_SIZE)
        )
        chunks = result.scalars().all()

        count = 0
        for chunk in chunks:
            embedding = await _generate_embedding(f"{chunk.title}\n{chunk.chunk_text}")
            if embedding is None:
                continue
            chunk.embedding = embedding
            count += 1

        if count > 0:
            await db.commit()
            logger.info("Clinical KB: embedded %d chunks", count)
        return count

    except Exception as exc:
        logger.warning("clinical_kb embed_all_pending failed silently: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return 0


async def embed_pending_chapters(db: AsyncSession) -> int:
    """
    Gera embeddings para Chapter records com content_type='text' que ainda
    não têm embedding.

    Retorna a quantidade de capítulos efetivamente processados nesta chamada.
    Seguro para ser chamado múltiplas vezes (idempotente).

    Apenas capítulos de texto são processados — capítulos de vídeo e áudio
    não possuem conteúdo textual significativo para embedding.
    """
    from app.models.program import Chapter

    try:
        result = await db.execute(
            select(Chapter)
            .where(Chapter.content_type == "text")
            .where(Chapter.embedding.is_(None))
            .limit(_BATCH_SIZE)
        )
        chapters = result.scalars().all()

        count = 0
        for chapter in chapters:
            text_to_embed = f"{chapter.title}\n{chapter.content[:2000]}"
            embedding = await _generate_embedding(text_to_embed)
            if embedding is None:
                continue
            chapter.embedding = embedding
            count += 1

        if count > 0:
            await db.commit()
            logger.info("Chapters: embedded %d chapters", count)
        return count

    except Exception as exc:
        logger.warning("embed_pending_chapters failed silently: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return 0
