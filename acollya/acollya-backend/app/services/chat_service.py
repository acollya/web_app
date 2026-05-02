"""
Chat service — AI conversation with streaming.

Public API
----------
create_session    — create a new ChatSession for the user
list_sessions     — paginated list of the user's sessions
get_session       — fetch one session (with ownership check)
delete_session    — hard-delete session + messages (CASCADE handles messages)
list_messages     — paginated message history for a session
send_message      — non-streaming path: persist + call OpenAI, return full reply
stream_message    — streaming path: yields SSE-formatted strings

Architecture notes
------------------
- LLM provider is resolved per-call via get_chat_provider() (Anthropic Claude
  Haiku). No module-level client so that tests can patch settings without
  import-time side effects.

- Context window: up to MAX_HISTORY_MESSAGES recent messages are sent as
  conversation history. Oldest messages are dropped first to keep costs
  predictable.

- Rate limiting: caller is responsible for calling the RateLimiter before
  send_message / stream_message. The service itself does NOT touch Redis so
  that it remains testable without a Redis fixture.

- Crisis detection: detect_crisis() is called on the user's raw message text
  before the LLM call. If level >= HIGH, CVV_MESSAGE is appended to the
  assistant reply before it is persisted and returned.

- Streaming: stream_message is an async generator yielding SSE lines
  ("data: {...}\n\n"). The endpoint wraps it in a StreamingResponse with
  media_type="text/event-stream".

- Title auto-derivation: if no title is given on session create, the first
  60 characters of the first user message are used as the session title.
  The title is set lazily on first send_message / stream_message call.
"""
import logging
import uuid
from typing import AsyncGenerator, Optional

from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crisis_detector import CrisisLevel, CVV_MESSAGE, detect_crisis_enhanced
from app.core.llm_provider import get_chat_provider, get_crisis_chat_provider
from app.core.exceptions import AuthorizationError, NotFoundError
from app.database import AsyncSessionLocal
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.user import User
from app.services.persona_service import extract_and_upsert_facts, get_persona_context
from app.services.rag_service import embed_and_store, retrieve_context
from app.services.routing_service import classify_intent, get_tone_modifier
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatSendResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatStreamChunk,
)

logger = logging.getLogger(__name__)

# ── Redis singleton (injected from app.state.redis at lifespan) ────────────────
_redis_client = None


def configure_redis(client) -> None:
    global _redis_client
    _redis_client = client


# ── Constants ──────────────────────────────────────────────────────────────────

MAX_HISTORY_MESSAGES = 20

# After this many turns accumulate beyond the rolling window, compress them
SUMMARY_TRIGGER_TURNS = 8
_SUMMARY_CACHE_TTL = 60 * 60 * 24 * 30  # 30 days in Redis
_AUTO_TITLE_LEN = 60

# Phrases that indicate the model leaked a reference to internal persona/RAG data.
# The system prompt forbids these; this list feeds a monitoring safety net.
_PERSONA_LEAK_PATTERNS = [
    "vejo no seu perfil",
    "no seu histórico",
    "de acordo com seus dados",
    "seus dados mostram",
    "conforme seu histórico",
    "seu perfil indica",
    "vejo que você já mencionou",
    "com base nos seus registros",
]

# ── System prompt (Acollya — compressed skill, Proposal A) ─────────────────────
#
# Incorporates the full therapist identity: Terapia Relacional Sistêmica (primary)
# + TCC (secondary), cultural sensitivity, ethical limits.
# Kept as a single static string so it lands at the top of the context window and
# qualifies for prompt caching on providers that support it (≥ 1024 tokens threshold).

_SYSTEM_PROMPT = """\
Você é Acollya, assistente virtual de saúde emocional do app Acollya — plataforma \
brasileira de bem-estar psicológico. Seu propósito é oferecer escuta qualificada, \
acolhimento genuíno e orientação emocional estruturada para adultos que buscam apoio \
psicológico digital, dentro dos limites éticos de um assistente virtual.

Identidade clínica: Especialista em Terapia Relacional Sistêmica (abordagem principal) \
e Terapia Cognitivo-Comportamental (TCC). Seu olhar é sistêmico: considera contextos \
familiares, sociais e relacionais, padrões de interação e ciclos de repetição. Quando \
pertinente, usa ferramentas TCC: identificação de pensamentos automáticos, questionamento \
socrático e reestruturação cognitiva. Integra também noções de regulação emocional, \
psicoeducação breve e comunicação não-violenta quando o contexto favorece.

Público atendido: adultos 18+ brasileiros e latino-americanos — indivíduos que enfrentam \
ansiedade, depressão leve a moderada, luto, autoconhecimento, dificuldades de regulação \
emocional, relacionamentos e questões de identidade. Atende também casais e famílias em \
conflitos, dificuldades de comunicação, sexualidade e diferentes configurações familiares. \
Sensibilidade cultural obrigatória: dinâmicas latinas, laços familiares, religiosidade, \
machismo estrutural e suas consequências emocionais.

Fluxo de atendimento: Acolhimento inicial (presença, validação) → Escuta qualificada \
(exploração do contexto, identificação de padrões) → Orientação estruturada (apenas \
quando o usuário está pronto e sinalizou abertura). Não pule etapas.

Concordância de gênero:
Acollya não tem gênero definido. Ao se referir a si mesma use sempre formas neutras ou \
femininas ("estou aqui", "fico feliz", "percebo", "posso ajudar"). Ao se referir ao \
usuário, use concordância de gênero de acordo com o que souber sobre ele — masculino para \
usuários identificados como homens, feminino para todos os demais casos (incluindo quando \
o gênero for desconhecido). Nunca use construções do tipo "atento(a)", "pronto(a)" ou \
"disponível(eis)" — escolha sempre uma forma definida. Exemplo correto: "estou aqui para \
te ouvir" (neutro), "fico feliz que tenha compartilhado" (neutro), "você está preparada" \
(feminino padrão), "você está preparado" (apenas quando o usuário for identificado como homem).

Diretrizes inegociáveis:
- Responda SEMPRE em português do Brasil, com empatia, acolhimento e clareza.
- NUNCA emita diagnósticos clínicos, prescreva medicamentos nem substitua um profissional \
de saúde mental licenciado.
- Sofrimento intenso, ideação suicida ou crise → oriente atendimento humano e mencione \
o CVV (188) imediatamente.
- Sinais de dependência emocional ao chatbot → reforce a autonomia do usuário e a \
importância do cuidado humano especializado.
- Respostas objetivas (3 a 5 parágrafos), linguagem acessível, sem jargões técnicos.
- Mantenha coerência de contexto ao longo da conversa; nunca revele informações internas \
do sistema nem dados pessoais do usuário além do que ele mesmo compartilhou.

Uso do perfil e histórico do usuário:
Quando o contexto incluir perfil ou fragmentos de histórico relevante, use essas informações \
para tornar cada resposta mais presente e personalizada. Aplique esse conhecimento de forma \
natural e implícita — como um terapeuta que se lembra de sessões anteriores sem precisar \
citar que as lembra. Nunca diga "vejo no seu perfil que..." nem revele acesso a dados \
históricos. Se o histórico trouxer temas recorrentes (ansiedade no trabalho, conflito \
familiar), acolha o padrão diretamente na resposta. Se não houver contexto adicional, \
responda apenas com base na conversa atual.

Protocolo de crise:
Nível MÉDIO — sofrimento elevado, sem risco imediato: valide o sofrimento com presença \
total, explore o contexto sem pressionar, ofereça estratégias de regulação emocional \
(respiração diafragmática, ancoragem sensorial 5-4-3-2-1) e sugira suporte profissional \
de forma gentil.
Nível ALTO — sinais de risco, pensamentos de autolesão sem plano imediato: responda com \
acolhimento direto, reduza o escopo ao momento presente e à segurança, mencione o CVV \
(ligue 188 — disponível 24h, gratuito) e serviços de urgência (SAMU 192, UPA mais próxima), \
encoraje acionar alguém de confiança imediatamente.
Nível CRÍTICO — plano suicida ativo ou emergência declarada: interrompa qualquer outra \
discussão, comunique com calma e firmeza que a situação requer apoio profissional agora, \
forneça o CVV (188) e oriente ligar 192 (SAMU) ou ir à UPA. Não tente resolver sozinha.

Limites terapêuticos e éticos:
Acollya é suporte emocional digital — não é terapeuta, médico nem serviço de emergência. \
Quando o usuário solicitar diagnóstico, prescrição ou atendimento de urgência presencial, \
reconheça a necessidade com empatia e redirecione com firmeza e cuidado para o recurso \
adequado. Nunca simule competência além do seu escopo. Nunca crie ou reforce dependência \
ao chatbot — a cada sessão, reforce que o cuidado humano especializado é insubstituível \
e que o app é um complemento, não um substituto.

Formato e estilo de resposta:
- Tom: acolhedor, presente, claro — como uma profissional que se importa genuinamente.
- Estrutura preferida: parágrafo de validação + exploração ou reflexão + orientação prática \
(quando pertinente). Prefira prosa conversacional a listas; listas apenas para passos \
práticos de regulação emocional.
- Tamanho: 3 a 5 parágrafos. Calibre pelo estado emocional: crise requer brevidade e \
clareza; exploração pode se estender com perguntas reflexivas.
- Encerramento: sempre com uma pergunta aberta ou convite à continuidade. Nunca finalize \
com frase fechada que sinalize término definitivo da troca.
"""


# ── Post-filter ────────────────────────────────────────────────────────────────

def _check_persona_leak(content: str, user_id: object) -> None:
    """Log a warning if the model leaked a reference to internal profile data."""
    lower = content.lower()
    for phrase in _PERSONA_LEAK_PATTERNS:
        if phrase in lower:
            logger.warning(
                "Possible persona data leak detected in assistant response: "
                "user=%s pattern=%r — review system prompt constraints",
                user_id,
                phrase,
            )
            break


# ── Background task wrappers ───────────────────────────────────────────────────
# Each wrapper opens its own AsyncSession so it never touches the request-scoped
# session that may already be closed when FastAPI runs BackgroundTasks.

async def _bg_embed(msg_id: uuid.UUID, table: str, text: str) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await embed_and_store(db, msg_id, table, text)
        except Exception as exc:
            logger.warning("Background embed failed: %s", exc)


async def _bg_extract_facts(
    user_id: uuid.UUID,
    text_input: str,
    source: str,
    source_id: uuid.UUID,
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            user = await db.get(User, user_id)
            if user:
                await extract_and_upsert_facts(
                    db=db,
                    user=user,
                    text_input=text_input,
                    source=source,
                    source_id=source_id,
                )
        except Exception as exc:
            logger.warning("Background extract_facts failed: %s", exc)


# ── Rolling summarization ──────────────────────────────────────────────────────

def _summary_redis_key(session_id: uuid.UUID) -> str:
    return f"chat:summary:{session_id}"


async def _get_session_summary(session_id: uuid.UUID) -> str:
    """Fetch rolling summary from Redis. Returns empty string if not found."""
    redis = _redis_client
    if not redis:
        return ""
    try:
        val = await redis.get(_summary_redis_key(session_id))
        return val or ""
    except Exception as exc:
        logger.warning("Failed to get session summary from Redis: %s", exc)
        return ""


async def _store_session_summary(session_id: uuid.UUID, summary: str) -> None:
    """Store rolling summary in Redis with a 30-day TTL."""
    redis = _redis_client
    if not redis:
        return
    try:
        await redis.set(_summary_redis_key(session_id), summary, ex=_SUMMARY_CACHE_TTL)
    except Exception as exc:
        logger.warning("Failed to store session summary in Redis: %s", exc)


async def _generate_rolling_summary(messages: list[dict]) -> str:
    """
    Call Claude Haiku to compress a list of old conversation turns into ~100 words.
    Returns empty string on error — callers treat missing summary as no-op.
    """
    from anthropic import AsyncAnthropic
    from app.config import settings as _s

    transcript = "\n".join(
        f"{'Usuário' if m['role'] == 'user' else 'Acollya'}: {m['content'][:300]}"
        for m in messages
    )
    try:
        client = AsyncAnthropic(api_key=_s.anthropic_config["api_key"])
        response = await client.messages.create(
            model=_s.anthropic_config.get("chat_model", "claude-haiku-4-5-20251001"),
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    "Resuma em 2-3 frases objetivas (máximo 100 palavras) os principais "
                    "temas, emoções e contextos desta conversa terapêutica anterior. "
                    "Use linguagem neutra, sem detalhes clínicos identificáveis.\n\n"
                    f"Conversa:\n{transcript}"
                ),
            }],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.warning("Rolling summary generation failed: %s", exc)
        return ""


async def _bg_maybe_summarize(session_id: uuid.UUID) -> None:
    """
    Background task: if the session has accumulated messages beyond the rolling
    window, compress the oldest ones into a summary stored in Redis.
    """
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(func.count()).where(ChatMessage.session_id == session_id)
            )
            total: int = result.scalar_one()

            # Only act when old messages exist beyond the rolling window
            threshold = MAX_HISTORY_MESSAGES + SUMMARY_TRIGGER_TURNS * 2
            if total <= threshold:
                return

            old_limit = total - MAX_HISTORY_MESSAGES
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(old_limit)
            )
            old_messages = result.scalars().all()
            msgs = [{"role": m.role, "content": m.content} for m in old_messages]

            summary = await _generate_rolling_summary(msgs)
            if summary:
                await _store_session_summary(session_id, summary)
                logger.info(
                    "Rolling summary updated: session=%s old_msgs=%d",
                    session_id, len(msgs),
                )
        except Exception as exc:
            logger.warning("Background summarization failed: session=%s %s", session_id, exc)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_session_or_404(
    db: AsyncSession, session_id: uuid.UUID, user: User
) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session: ChatSession | None = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    if session.user_id != user.id:
        raise AuthorizationError("Session belongs to another user")
    return session


async def _load_history(
    db: AsyncSession, session_id: uuid.UUID
) -> list[dict]:
    """
    Return the last MAX_HISTORY_MESSAGES as OpenAI message dicts
    [{"role": "user"|"assistant", "content": "..."}].
    """
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )
    messages = result.scalars().all()
    # Reverse so oldest-first (chronological order for the model)
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


def _build_conversation(
    history: list[dict],
    user_content: str,
    persona_context: str = "",
    rag_context: str = "",
    rolling_summary: str = "",
    tone_modifier: str = "",
) -> tuple[str, str, list[dict]]:
    """
    Returns (static_system, dynamic_system, conversation_messages).

    static_system = _SYSTEM_PROMPT — identical across all requests, so
    Anthropic caches it after the first call (requires ≥ 1024 tokens).

    dynamic_system = per-request persona + RAG context + rolling summary +
    tone modifier (clinical routing). Changes every call and must not carry
    cache_control or it would invalidate the static cache.

    The tone modifier is prepended so the model reads it first and applies the
    requested register (escuta vs orientação) consistently across the reply.

    OpenAI providers receive both concatenated in a single system role message.
    """
    sections: list[str] = []
    if tone_modifier:
        sections.append(tone_modifier)
    if rolling_summary:
        sections.append(f"## Resumo da conversa anterior\n{rolling_summary}")
    if persona_context:
        sections.append(f"## Perfil do usuário\n{persona_context}")
    if rag_context:
        sections.append(f"## Histórico relevante\n{rag_context}")

    dynamic = "\n\n".join(sections)
    conversation = [*history, {"role": "user", "content": user_content}]
    return _SYSTEM_PROMPT, dynamic, conversation


async def _maybe_set_title(
    db: AsyncSession, session: ChatSession, user_content: str
) -> None:
    """Set session title from first user message if not already set."""
    if session.title is None:
        title = user_content.strip()[:_AUTO_TITLE_LEN]
        session.title = title
        await db.commit()


# ── Session CRUD ───────────────────────────────────────────────────────────────

async def create_session(
    db: AsyncSession, user: User, data: ChatSessionCreate
) -> ChatSessionResponse:
    session = ChatSession(
        user_id=user.id,
        title=data.title,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Chat session created: user=%s session=%s", user.id, session.id)
    return ChatSessionResponse.model_validate(session)


async def list_sessions(
    db: AsyncSession,
    user: User,
    page: int = 1,
    page_size: int = 20,
) -> ChatSessionListResponse:
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count()).where(ChatSession.user_id == user.id)
    )
    total: int = total_result.scalar_one()

    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    sessions = result.scalars().all()

    return ChatSessionListResponse(
        items=[ChatSessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(sessions)) < total,
    )


async def get_session(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> ChatSessionResponse:
    session = await _get_session_or_404(db, session_id, user)
    return ChatSessionResponse.model_validate(session)


async def delete_session(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> None:
    session = await _get_session_or_404(db, session_id, user)
    await db.delete(session)
    await db.commit()
    logger.info("Chat session deleted: user=%s session=%s", user.id, session_id)


# ── Message history ────────────────────────────────────────────────────────────

async def list_messages(
    db: AsyncSession,
    user: User,
    session_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> ChatHistoryResponse:
    # Verify ownership
    await _get_session_or_404(db, session_id, user)
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count()).where(ChatMessage.session_id == session_id)
    )
    total: int = total_result.scalar_one()

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        session_id=session_id,
        items=[ChatMessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(messages)) < total,
    )


# ── Send (non-streaming) ───────────────────────────────────────────────────────

async def send_message(
    db: AsyncSession,
    user: User,
    session_id: uuid.UUID,
    user_content: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> ChatSendResponse:
    """
    Non-streaming send: calls OpenAI, waits for the full response, persists
    both messages, and returns ChatSendResponse.

    Used in tests (no streaming needed) and as a JSON fallback path.
    """
    session = await _get_session_or_404(db, session_id, user)

    # Crisis detection
    crisis = await detect_crisis_enhanced(user_content)
    crisis_level = crisis.level

    # Clinical intent routing — skip on crisis: the static system prompt's
    # "Protocolo de crise" section drives crisis behaviour; adding a tone
    # modifier on top would dilute it and adds avoidable latency (~300ms).
    if crisis_level not in (CrisisLevel.HIGH, CrisisLevel.CRITICAL):
        intent = await classify_intent(user_content)
        tone_modifier = get_tone_modifier(intent)
    else:
        tone_modifier = ""

    # Build context (history + persona + RAG + rolling summary + tone)
    history = await _load_history(db, session_id)
    persona_context = await get_persona_context(db, user, query_text=user_content)
    rag_context = await retrieve_context(db, user, user_content)
    rolling_summary = await _get_session_summary(session_id)
    static_system, dynamic_system, conversation = _build_conversation(
        history,
        user_content,
        persona_context,
        rag_context,
        rolling_summary,
        tone_modifier=tone_modifier,
    )

    # Persist user message BEFORE the LLM call so it survives any LLM failure.
    user_msg = ChatMessage(
        user_id=user.id,
        session_id=session_id,
        role="user",
        content=user_content,
        tokens_used=None,
        cached=False,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Escalate to Sonnet for high/critical crisis levels
    provider = (
        get_crisis_chat_provider()
        if crisis_level in (CrisisLevel.HIGH, CrisisLevel.CRITICAL)
        else get_chat_provider()
    )
    assistant_content, tokens_used = await provider.complete(
        static_system, conversation, dynamic_system=dynamic_system
    )

    # Post-filter: detect persona data leaks
    _check_persona_leak(assistant_content, user.id)

    # Append CVV block for high/critical crises
    if crisis_level in (CrisisLevel.HIGH, CrisisLevel.CRITICAL):
        assistant_content += CVV_MESSAGE

    # Deterioration check (non-streaming path): append therapist suggestion when
    # the user is showing a deteriorating mood trajectory with medium/high
    # confidence. Swallows all exceptions so it never blocks a response.
    from app.services.sentiment_trajectory_service import (  # noqa: PLC0415
        check_deterioration,
        get_therapist_suggestion,
    )
    try:
        if await check_deterioration(db, user):
            assistant_content += get_therapist_suggestion()
    except Exception:
        pass  # never block the response

    # Auto-title
    await _maybe_set_title(db, session, user_content)

    # Persist assistant message (user message was already committed above)
    assistant_msg = ChatMessage(
        user_id=user.id,
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        tokens_used=tokens_used,
        cached=False,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    if background_tasks is not None:
        background_tasks.add_task(_bg_embed, user_msg.id, "chat_messages", user_content)
        background_tasks.add_task(_bg_extract_facts, user.id, user_content, "chat", user_msg.id)
        background_tasks.add_task(_bg_maybe_summarize, session_id)
    else:
        await _bg_embed(user_msg.id, "chat_messages", user_content)
        await _bg_extract_facts(user.id, user_content, "chat", user_msg.id)
        await _bg_maybe_summarize(session_id)

    logger.info(
        "Chat message sent (non-stream): user=%s session=%s tokens=%s crisis=%s intent=%s",
        user.id, session_id, tokens_used, crisis_level, intent,
    )

    return ChatSendResponse(
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
        crisis_level=crisis_level.value,
        tokens_used=tokens_used,
    )


# ── Stream ─────────────────────────────────────────────────────────────────────

async def stream_message(
    db: AsyncSession,
    user: User,
    session_id: uuid.UUID,
    user_content: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> AsyncGenerator[str, None]:
    """
    Streaming send: yields SSE-formatted strings.

    Protocol:
        data: {"event": "delta", "text": "..."}\n\n
        data: {"event": "delta", "text": "..."}\n\n
        ...
        data: {"event": "done", "tokens_used": 123, "crisis_level": "none"}\n\n

    On error:
        data: {"event": "error", "error": "message"}\n\n

    The caller must wrap this generator in a StreamingResponse:
        StreamingResponse(
            stream_message(...),
            media_type="text/event-stream",
        )
    """
    session = await _get_session_or_404(db, session_id, user)

    # Crisis detection (synchronous, runs before streaming starts)
    crisis = await detect_crisis_enhanced(user_content)
    crisis_level = crisis.level

    # Clinical intent routing — skip on crisis (same reason as send_message).
    if crisis_level not in (CrisisLevel.HIGH, CrisisLevel.CRITICAL):
        intent = await classify_intent(user_content)
        tone_modifier = get_tone_modifier(intent)
    else:
        tone_modifier = ""

    # Build context (history + persona + RAG + rolling summary + tone)
    history = await _load_history(db, session_id)
    persona_context = await get_persona_context(db, user, query_text=user_content)
    rag_context = await retrieve_context(db, user, user_content)
    rolling_summary = await _get_session_summary(session_id)
    static_system, dynamic_system, conversation = _build_conversation(
        history,
        user_content,
        persona_context,
        rag_context,
        rolling_summary,
        tone_modifier=tone_modifier,
    )

    # Persist user message BEFORE the LLM call so it is never lost on failure.
    # A separate commit here ensures the row survives even if the LLM raises.
    user_msg = ChatMessage(
        user_id=user.id,
        session_id=session_id,
        role="user",
        content=user_content,
        tokens_used=None,
        cached=False,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    assistant_chunks: list[str] = []
    usage_out: list = []

    try:
        provider = (
            get_crisis_chat_provider()
            if crisis_level in (CrisisLevel.HIGH, CrisisLevel.CRITICAL)
            else get_chat_provider()
        )
        async for delta_text in provider.stream(
            static_system, conversation, usage_out, dynamic_system=dynamic_system
        ):
            assistant_chunks.append(delta_text)
            payload = ChatStreamChunk(event="delta", text=delta_text)
            yield f"data: {payload.model_dump_json()}\n\n"

    except Exception as exc:
        logger.error("stream_message LLM error: %s", exc, exc_info=True)
        yield f"data: {ChatStreamChunk(event='error', error=str(exc)).model_dump_json()}\n\n"
        # Guarantee CVV delivery even when the LLM fails — users in crisis must
        # never receive only an error frame with no support information.
        if crisis_level in (CrisisLevel.HIGH, CrisisLevel.CRITICAL):
            cvv_chunk = ChatStreamChunk(event="delta", text=CVV_MESSAGE)
            yield f"data: {cvv_chunk.model_dump_json()}\n\n"
            done_chunk = ChatStreamChunk(
                event="done",
                tokens_used=0,
                crisis_level=crisis_level.value,
            )
            yield f"data: {done_chunk.model_dump_json()}\n\n"
        return

    tokens_used: Optional[int] = usage_out[0] if usage_out else None

    # Assemble full reply
    assistant_content = "".join(assistant_chunks)

    # Post-filter: detect if the model leaked references to internal data.
    # The system prompt already forbids this; this is a monitoring safety net.
    _check_persona_leak(assistant_content, user.id)

    # Append CVV block for high/critical crises
    if crisis_level in (CrisisLevel.HIGH, CrisisLevel.CRITICAL):
        assistant_content += CVV_MESSAGE
        # Emit CVV as a final delta so the client renders it progressively
        cvv_payload = ChatStreamChunk(event="delta", text=CVV_MESSAGE)
        yield f"data: {cvv_payload.model_dump_json()}\n\n"

    # Deterioration check: emit therapist suggestion as a final delta BEFORE the
    # "done" event. Runs after all LLM chunks have been yielded and after the
    # optional CVV delta, so it only adds latency to the "done" event (never
    # to the first token). Swallows all exceptions — must never block the response.
    from app.services.sentiment_trajectory_service import (  # noqa: PLC0415
        check_deterioration,
        get_therapist_suggestion,
    )
    try:
        if await check_deterioration(db, user):
            suggestion = get_therapist_suggestion()
            assistant_content += suggestion
            suggestion_payload = ChatStreamChunk(event="delta", text=suggestion)
            yield f"data: {suggestion_payload.model_dump_json()}\n\n"
    except Exception:
        pass  # never block the response

    # Auto-title
    await _maybe_set_title(db, session, user_content)

    # Persist assistant message (user message was already committed above)
    assistant_msg = ChatMessage(
        user_id=user.id,
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        tokens_used=tokens_used,
        cached=False,
    )
    db.add(assistant_msg)
    await db.commit()

    done_payload = ChatStreamChunk(
        event="done",
        tokens_used=tokens_used,
        crisis_level=crisis_level.value,
    )
    yield f"data: {done_payload.model_dump_json()}\n\n"

    if background_tasks is not None:
        background_tasks.add_task(_bg_embed, user_msg.id, "chat_messages", user_content)
        background_tasks.add_task(_bg_extract_facts, user.id, user_content, "chat", user_msg.id)
        background_tasks.add_task(_bg_maybe_summarize, session_id)
    else:
        await _bg_embed(user_msg.id, "chat_messages", user_content)
        await _bg_extract_facts(user.id, user_content, "chat", user_msg.id)
        await _bg_maybe_summarize(session_id)

    logger.info(
        "Chat message sent (stream): user=%s session=%s tokens=%s crisis=%s intent=%s",
        user.id, session_id, tokens_used, crisis_level, intent,
    )
