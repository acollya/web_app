"""
User service — business logic for /users/me endpoints.

Operations:
  get_me(user)                              -> UserResponse (thin wrapper, no DB query needed)
  update_me(db, user, data)                 -> UserResponse
  change_password(db, redis, user, data)    -> UserResponse
  delete_me(db, user, redis)                -> None  (LGPD right-to-erasure)

LGPD deletion strategy (revisado 2026-08-28 — ADR-011):
  Conteúdo SENSÍVEL de saúde (LGPD Art. 11) é apagado DEFINITIVAMENTE:
  chat (mensagens + sessões), diário e check-ins de humor contêm texto livre
  do usuário que frequentemente inclui dado sensível/PII — pseudonimizar a
  tabela users não anonimiza esse conteúdo. Nenhuma retenção para ML sem
  consentimento explícito (não implementado; se um dia existir, exigirá
  opt-in específico e nova revisão de compliance).

What is DELETED on erasure request:
  - users fields: all PII overwritten (email, name, phone, birth_date, gender,
    google_id, apple_id, password_hash, push tokens, revenue_cat_id)
  - chat_messages + chat_sessions: conteúdo integral + embeddings
  - journal_entries: conteúdo integral + embeddings
  - mood_checkins: humor, notas, insights + embeddings
  - user_persona_facts: extracted identity facts ("lives in X", "has anxiety")
  - user_sessions: device fingerprints (user_agent, device_type)
  - Redis refresh_jti:{jti} keys: all active refresh tokens revoked

What is PRESERVED (pseudônimo, sem conteúdo sensível):
  - crisis_events — trilha probatória do protocolo de crise. Base de
    conservação pós-término: LGPD Art. 16, I (cumprimento de obrigação
    legal/regulatória) e exercício regular de direitos (Art. 7 §3) —
    dados minimizados (nível, cvv_shown, timestamp; sem conteúdo).
    Nota: é dado PSEUDÔNIMO (FK user_id → linha anonimizada), não anônimo.
    Prazo de retenção e expurgo: pendente de definição jurídica
    (legal-checklist).
  - program_progress, appointments, subscriptions — registros operacionais
    e financeiros referenciando apenas a UUID anonimizada (Art. 12).
"""
import logging
import uuid
from datetime import UTC, datetime
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password
from app.core.exceptions import AuthenticationError, ValidationError
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.journal_entry import JournalEntry
from app.models.mood_checkin import MoodCheckin
from app.models.user import User
from app.models.user_persona_fact import UserPersonaFact
from app.models.user_session import UserSession
from app.schemas.user import PasswordChangeRequest, UserResponse, UserUpdate
from app.services import auth_service

logger = logging.getLogger(__name__)


def get_me(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


async def update_me(db: AsyncSession, user: User, data: UserUpdate) -> UserResponse:
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def change_password(
    db: AsyncSession,
    redis: Redis,
    user: User,
    data: PasswordChangeRequest,
) -> UserResponse:
    """
    Change the authenticated user's password and revoke every active session.

    Rules:
      1. SSO-only accounts (no password_hash) cannot use this endpoint.
      2. The current password must verify (constant-time bcrypt check).
      3. The new password may not be identical to the current one.
      4. On success, ALL refresh tokens are revoked — the client that just
         changed the password will need to log in again. This is intentional:
         "change password" implies "kick every session out".

    The access token used to authenticate this very request is NOT revoked
    (access tokens are stateless and short-lived: max 15 minutes). It will
    expire naturally and the client will be unable to refresh it.
    """
    if not user.password_hash:
        raise ValidationError(
            "This account uses single sign-on (Google or Apple) and has no password. "
            "Set a password by signing in via your SSO provider's account settings."
        )

    if not verify_password(data.current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect")

    if data.new_password == data.current_password:
        raise ValidationError("New password must be different from the current password")

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    await db.refresh(user)

    revoked = await auth_service.revoke_all_sessions(redis, str(user.id))
    logger.info("User %s changed password — revoked %d session(s)", user.id, revoked)

    return UserResponse.model_validate(user)


async def delete_me(
    db: AsyncSession,
    user: User,
    redis: Optional[Redis] = None,
) -> None:
    """
    LGPD Art. 18 — right to erasure (revisado 2026-08-28, ADR-011).

    Apaga DEFINITIVAMENTE todo o conteúdo sensível de saúde (Art. 11):
    chat, diário, humor, persona e sessões — texto livre do usuário não é
    anonimizável por pseudonimização da tabela users. Preserva apenas
    registros pseudônimos sem conteúdo sensível: crisis_events (probatório),
    program_progress, appointments, subscriptions.

    Execution order (1-6 atômicos no mesmo commit; 7 best-effort):
      1. Hard-delete chat_messages e chat_sessions (conteúdo + embeddings).
      2. Hard-delete journal_entries (conteúdo + embeddings).
      3. Hard-delete mood_checkins (notas + embeddings).
      4. Hard-delete user_persona_facts.
      5. Hard-delete user_sessions.
      6. Anonymise PII na linha users + is_active=False.
      7. Revoke all active refresh tokens in Redis.
    """
    user_id_str = str(user.id)

    # 1. Conteúdo sensível: chat (mensagens antes das sessões — FK)
    await db.execute(sql_delete(ChatMessage).where(ChatMessage.user_id == user.id))
    await db.execute(sql_delete(ChatSession).where(ChatSession.user_id == user.id))

    # 2. Conteúdo sensível: diário
    await db.execute(sql_delete(JournalEntry).where(JournalEntry.user_id == user.id))

    # 3. Conteúdo sensível: humor
    await db.execute(sql_delete(MoodCheckin).where(MoodCheckin.user_id == user.id))

    # 4. Delete identity-linked facts
    await db.execute(sql_delete(UserPersonaFact).where(UserPersonaFact.user_id == user.id))

    # 5. Delete device-fingerprint sessions
    await db.execute(sql_delete(UserSession).where(UserSession.user_id == user.id))

    # 6. Anonymise PII columns on the user row
    anon_id = str(uuid.uuid4())[:8]
    user.email = f"deleted_{anon_id}@acollya.invalid"
    user.name = "Conta encerrada"
    user.phone = None
    user.birth_date = None
    user.gender = None
    user.google_id = None
    user.apple_id = None
    user.password_hash = None
    user.push_token_fcm = None
    user.push_token_apns = None
    user.revenue_cat_id = None
    user.is_active = False
    user.is_anonymized = True
    user.anonymized_at = datetime.now(UTC)

    # Commit steps 1-6 atomically
    await db.commit()
    logger.info(
        "User %s erased (LGPD): chat, journal, mood, persona and sessions hard-deleted; PII anonymised",
        user.id,
    )

    # 7. Revoke all active refresh tokens in Redis (best-effort — must not raise)
    if redis is not None:
        await _revoke_user_refresh_tokens(redis, user_id_str)


async def _revoke_user_refresh_tokens(redis: Redis, user_id: str) -> None:
    """
    Revoke every active refresh-token session for user_id.

    Primary path uses the `user_sessions:{user_id}` secondary index (O(1)).
    A SCAN fallback is kept for backward compatibility with any pre-index
    jtis still floating around Redis (covers in-flight tokens issued before
    the index was deployed).

    Errors are caught and logged — token revocation must never fail the
    deletion request because the DB transaction has already committed.
    """
    try:
        revoked = await auth_service.revoke_all_sessions(redis, user_id)
        logger.info(
            "Revoked %d refresh-token session(s) for deleted user %s (via index)",
            revoked,
            user_id,
        )

        # Fallback: SCAN for orphan keys not present in the index
        # (legacy data written before the secondary index existed).
        orphans: list[str] = []
        cursor: int = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="refresh_jti:*", count=100)
            for key in keys:
                value = await redis.get(key)
                if value == user_id:
                    orphans.append(key)
            if int(cursor) == 0:
                break

        if orphans:
            await redis.delete(*orphans)
            logger.info(
                "Revoked %d orphan refresh token(s) for deleted user %s (via SCAN)",
                len(orphans),
                user_id,
            )

    except Exception as exc:  # noqa: BLE001
        # Non-fatal: tokens will naturally expire within 30 days.
        # The user row is already deactivated so _validate_jti in auth_service
        # will reject any attempt to use them before they expire.
        logger.error(
            "Failed to revoke Redis refresh tokens for user %s: %s",
            user_id,
            exc,
            exc_info=True,
        )


# ── LGPD: consentimentos granulares (Art. 11) ─────────────────────────────────

async def update_consents(
    db: AsyncSession,
    user: User,
    terms_accepted: bool,
    health_data_consent: bool,
    birth_date,
) -> UserResponse:
    """
    Registra o aceite granular pós-cadastro (fluxo SSO usa isso após o modal):
    termos + versão vigente, consentimento específico de dados de saúde
    (Art. 11) e data de nascimento com verificação de idade mínima.

    Levanta ValidationError-equivalente (ValueError → 422 via schema) para
    idade abaixo do mínimo — a conta recém-criada deve então ser descartada
    pelo cliente via DELETE /users/me.
    """
    from app.config import settings
    from app.core.exceptions import ValidationError

    today = datetime.now(UTC).date()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    if age < settings.minimum_age_years:
        raise ValidationError(
            f"O Acollya é destinado a maiores de {settings.minimum_age_years} anos."
        )
    if birth_date.year < 1900:
        raise ValidationError("Data de nascimento inválida.")

    now = datetime.now(UTC)
    user.terms_accepted = terms_accepted
    user.terms_accepted_date = now
    user.terms_version = settings.terms_version
    user.health_data_consent = health_data_consent
    user.health_data_consent_date = now
    user.birth_date = birth_date
    await db.commit()
    await db.refresh(user)
    logger.info("User %s consents recorded (terms v%s, health=%s)",
                user.id, settings.terms_version, health_data_consent)
    return UserResponse.model_validate(user)


# ── LGPD Art. 18: portabilidade — exportação de dados ─────────────────────────

async def export_my_data(db: AsyncSession, user: User) -> dict:
    """
    Exporta todos os dados pessoais do usuário em formato estruturado (JSON).
    Embeddings vetoriais são omitidos (derivados técnicos, não são "dados
    fornecidos pelo titular" e são inúteis fora do sistema).
    """
    from sqlalchemy import select
    from app.models.program_progress import ProgramProgress
    from app.models.appointment import Appointment
    from app.models.crisis_event import CrisisEvent
    from app.models.subscription import Subscription

    def iso(dt) -> Optional[str]:
        return dt.isoformat() if dt else None

    moods = (await db.execute(
        select(MoodCheckin).where(MoodCheckin.user_id == user.id).order_by(MoodCheckin.created_at)
    )).scalars().all()
    journals = (await db.execute(
        select(JournalEntry).where(JournalEntry.user_id == user.id).order_by(JournalEntry.created_at)
    )).scalars().all()
    sessions = (await db.execute(
        select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.created_at)
    )).scalars().all()
    messages = (await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.created_at)
    )).scalars().all()
    facts = (await db.execute(
        select(UserPersonaFact).where(UserPersonaFact.user_id == user.id)
    )).scalars().all()
    progress = (await db.execute(
        select(ProgramProgress).where(ProgramProgress.user_id == user.id)
    )).scalars().all()
    appointments = (await db.execute(
        select(Appointment).where(Appointment.user_id == user.id)
    )).scalars().all()
    crisis = (await db.execute(
        select(CrisisEvent).where(CrisisEvent.user_id == user.id).order_by(CrisisEvent.created_at)
    )).scalars().all()
    subs = (await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )).scalars().all()

    return {
        "formato": "Exportação de dados pessoais — Acollya (LGPD Art. 18, portabilidade)",
        "gerado_em": datetime.now(UTC).isoformat(),
        "perfil": {
            "id": str(user.id),
            "nome": user.name,
            "email": user.email,
            "telefone": user.phone,
            "data_nascimento": iso(user.birth_date),
            "genero": user.gender,
            "plano": user.plan_code,
            "termos_aceitos_em": iso(user.terms_accepted_date),
            "versao_termos": user.terms_version,
            "consentimento_dados_saude": user.health_data_consent,
            "consentimento_dados_saude_em": iso(user.health_data_consent_date),
            "conta_criada_em": iso(user.created_at),
        },
        "registros_de_humor": [
            {"humor": m.mood, "intensidade": m.intensity, "nota": m.note,
             "insight_ia": m.ai_insight, "data": iso(m.created_at)}
            for m in moods
        ],
        "diario": [
            {"titulo": j.title, "conteudo": j.content, "reflexao_ia": j.ai_reflection,
             "criado_em": iso(j.created_at), "atualizado_em": iso(j.updated_at)}
            for j in journals
        ],
        "conversas": [
            {
                "sessao_id": str(s.id), "titulo": s.title, "criada_em": iso(s.created_at),
                "mensagens": [
                    {"autor": m.role, "conteudo": m.content, "data": iso(m.created_at)}
                    for m in messages if m.session_id == s.id
                ],
            }
            for s in sessions
        ],
        "fatos_de_personalizacao": [
            {"categoria": str(f.category), "fato": f.fact_text, "origem": f.source,
             "criado_em": iso(f.created_at)}
            for f in facts
        ],
        "progresso_em_programas": [
            {"programa_id": str(p.program_id), "capitulo_id": str(p.chapter_id),
             "concluido": p.completed, "concluido_em": iso(p.completed_at)}
            for p in progress
        ],
        "agendamentos": [
            {"data": iso(a.date) if hasattr(a.date, "isoformat") else str(a.date),
             "horario": str(a.time), "status": a.status, "criado_em": iso(a.created_at)}
            for a in appointments
        ],
        "eventos_de_crise": [
            {"nivel": c.crisis_level, "cvv_exibido": c.cvv_shown,
             "origem": c.source, "data": iso(c.created_at)}
            for c in crisis
        ],
        "assinaturas": [
            {"status": s.status, "provedor": getattr(s, "provider", None),
             "inicio": iso(getattr(s, "created_at", None)),
             "fim_do_periodo": iso(getattr(s, "current_period_end", None))}
            for s in subs
        ],
    }
