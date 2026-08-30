"""
storage_service — helpers S3 para mídia de usuário (Chat F2+).

Chaves são SEMPRE namespaced por user_id (`{prefixo}/{user_id}/{uuid}.{ext}`)
para permitir a deleção em cascata LGPD via delete_user_prefixes().
"""
import asyncio
import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)

# Prefixos de mídia por usuário — manter em sincronia com delete_user_prefixes
USER_MEDIA_PREFIXES = ("chat-audio", "tts")


def _client():
    return boto3.client("s3", region_name=settings.aws_region)


async def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    """Sobe um objeto para o bucket de mídia (roda o boto3 em thread)."""
    s3 = _client()
    await asyncio.to_thread(
        s3.put_object,
        Bucket=settings.media_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def presign(key: str, ttl_seconds: int = 3600) -> str:
    """URL pré-assinada de leitura (default 1h — permite replay no chat)."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.media_bucket, "Key": key},
        ExpiresIn=ttl_seconds,
    )


async def delete_user_prefixes(user_id: str) -> None:
    """
    LGPD: apaga TODOS os objetos de mídia do usuário (chat-audio/, tts/).
    Best-effort — nunca levanta exceção (chamado dentro do delete_me).
    """
    try:
        s3 = _client()
        for prefix in USER_MEDIA_PREFIXES:
            full_prefix = f"{prefix}/{user_id}/"
            paginator = s3.get_paginator("list_objects_v2")

            def _delete_all() -> int:
                count = 0
                for page in paginator.paginate(Bucket=settings.media_bucket, Prefix=full_prefix):
                    objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
                    if objs:
                        s3.delete_objects(
                            Bucket=settings.media_bucket, Delete={"Objects": objs}
                        )
                        count += len(objs)
                return count

            deleted = await asyncio.to_thread(_delete_all)
            if deleted:
                logger.info("S3 erasure: %d objeto(s) removidos de %s", deleted, full_prefix)
    except Exception as exc:
        logger.warning("S3 erasure best-effort falhou (user=%s): %s", user_id, exc)
