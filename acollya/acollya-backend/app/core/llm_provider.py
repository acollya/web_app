"""
LLM Provider abstraction — unified interface over OpenAI and Anthropic.

Design
------
Two concrete providers are offered:

  OpenAIProvider    — wraps AsyncOpenAI (embeddings, fallback tasks)
  AnthropicProvider — wraps AsyncAnthropic (chat + insights/reflections)

Both expose the same two methods:

  complete(system, messages, max_tokens) -> (content, tokens_used)
      Non-streaming call. Returns the full reply plus total token count.

  stream(system, messages, usage_out) -> AsyncGenerator[str, None]
      Streaming call. Yields text chunks. Appends tokens_used to usage_out
      when the stream finishes, so the caller can read it after exhausting
      the generator.

Extended thinking (AnthropicProvider only)
------------------------------------------
  AnthropicProvider accepts two extra constructor args:

    thinking        : bool = False  — enable extended thinking
    thinking_budget : int  = 2000   — max tokens the model may use for thinking

  When thinking=True, complete() sets max_tokens = thinking_budget + base_output
  automatically and filters out <thinking> blocks from the response, returning
  only the final user-visible text.
  When thinking=True, temperature is not accepted by the API and is omitted.

Token budgets
-------------
  _CHAT_STREAM_MAX_TOKENS   = 2000  — chat streaming (respostas terapêuticas densas)
  _INSIGHT_MAX_TOKENS       = 800   — insights e reflexões (texto curto, direto)
  _DEFAULT_MAX_TOKENS       = 1024  — fallback para chamadas genéricas

Temperature
-----------
  _INSIGHT_TEMPERATURE = 0.4  — aplicado em complete() quando thinking=False.
  Reduz variância nas respostas clínicas mantendo naturalidade.
  Não afeta chamadas com thinking ativo (ignorado pela API Anthropic).

Factory helpers
---------------
  get_chat_provider()    -> AnthropicProvider  (Claude Haiku, no thinking)
  get_insight_provider() -> AnthropicProvider  (Claude Haiku, thinking enabled)

Example usage (non-streaming)
------------------------------
    provider = get_insight_provider()
    content, tokens = await provider.complete(system_prompt, messages)

Example usage (streaming)
--------------------------
    provider = get_chat_provider()
    usage: list = []
    async for chunk in provider.stream(system_prompt, messages, usage):
        yield chunk
    tokens_used = usage[0] if usage else None
"""
import logging
import time
from typing import AsyncGenerator, Optional

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# ── Circuit breaker (chat-only) ────────────────────────────────────────────────
#
# Protects the main chat path against transient Anthropic outages. State is
# module-level (in-process): a single Lambda instance tracks its own recent
# failures; we explicitly do NOT push this to Redis because:
#   1. Redis adds latency to every chat call (the hot path).
#   2. Each Lambda container observes its own connectivity to Anthropic;
#      a per-instance breaker is the right granularity.
#   3. Concurrency=2 keeps the blast radius small even if one instance
#      stays "open" longer than another.
#
# Behaviour:
#   - Records timestamps of recent failures in a sliding window of
#     _CB_WINDOW_SECONDS.
#   - When _CB_FAILURE_THRESHOLD failures are observed inside that window,
#     the breaker opens for _CB_RESET_SECONDS — primary calls are skipped
#     and the fallback provider is used directly.
#   - Crisis and insight providers are NOT routed through the breaker:
#     crisis responses must never silently degrade to a lesser model, and
#     insights are background tasks that should fail loudly.

_CB_FAILURE_THRESHOLD = 3
_CB_RESET_SECONDS = 120
_CB_WINDOW_SECONDS = 60
_cb_failures: list[float] = []  # timestamps of recent failures
_cb_open_until: float = 0.0


def _cb_record_failure() -> None:
    """Record a primary-provider failure and possibly trip the breaker."""
    global _cb_open_until
    now = time.monotonic()
    # Evict timestamps older than the window
    cutoff = now - _CB_WINDOW_SECONDS
    while _cb_failures and _cb_failures[0] < cutoff:
        _cb_failures.pop(0)
    _cb_failures.append(now)
    if len(_cb_failures) >= _CB_FAILURE_THRESHOLD and _cb_open_until <= now:
        _cb_open_until = now + _CB_RESET_SECONDS
        logger.warning(
            "LLM circuit breaker OPEN: %d failures in %ds — falling back for %ds",
            len(_cb_failures), _CB_WINDOW_SECONDS, _CB_RESET_SECONDS,
        )


def _cb_is_open() -> bool:
    """Return True if the breaker is currently open (skip primary)."""
    global _cb_open_until
    now = time.monotonic()
    if _cb_open_until > now:
        return True
    if _cb_open_until and _cb_open_until <= now:
        # Reset window after cooldown
        _cb_open_until = 0.0
        _cb_failures.clear()
        logger.info("LLM circuit breaker CLOSED — resuming primary provider")
    return False

# Chat streaming: respostas terapêuticas podem ser densas (acolhimento + orientação).
_CHAT_STREAM_MAX_TOKENS = 2000

# Insights e reflexões: texto curto e direto — 800 tokens é mais que suficiente.
_INSIGHT_MAX_TOKENS = 800

# Fallback para chamadas genéricas (complete() sem thinking via base class).
_DEFAULT_MAX_TOKENS = 1024

# Temperature para complete() sem thinking — reduz variância em contexto clínico.
_INSIGHT_TEMPERATURE = 0.4

# Anthropic prompt-caching beta header.
# Caches system prompt across turns of the same conversation.
# Requires ≥ 1024 tokens in the cached block; silently skipped if not met.
_CACHE_BETA_HEADER = {"anthropic-beta": "prompt-caching-2024-07-31"}


def _system_blocks(static: str, dynamic: str = "") -> list[dict]:
    """
    Returns Anthropic system content blocks.

    The static block (identity, directives — identical across all requests)
    carries cache_control so Anthropic caches it after the first call.
    The dynamic block (per-request persona + RAG context) is appended without
    cache_control so it never invalidates the cached static block.

    Anthropic requires ≥ 1024 tokens in the cached block; _SYSTEM_PROMPT in
    chat_service.py is sized to exceed this threshold comfortably.
    """
    blocks: list[dict] = [
        {"type": "text", "text": static, "cache_control": {"type": "ephemeral"}}
    ]
    if dynamic:
        blocks.append({"type": "text", "text": dynamic})
    return blocks


# ── Base class ─────────────────────────────────────────────────────────────────

class LLMProvider:
    """Duck-typed base. Subclasses must implement complete() and stream()."""

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        *,
        dynamic_system: str = "",
    ) -> tuple[str, Optional[int]]:
        """
        Non-streaming completion.

        Parameters
        ----------
        system         : Static system prompt — cached by Anthropic when ≥ 1024 tokens.
        messages       : Conversation turns — [{"role": "user"|"assistant", "content": "..."}].
                         Do NOT include a system-role dict here; pass it via `system`.
        max_tokens     : Maximum tokens to generate.
        dynamic_system : Per-request context (persona, RAG) appended after the static
                         prompt without cache_control so it never invalidates the cache.

        Returns
        -------
        (content, tokens_used) — tokens_used is None if the provider does not
        report usage.
        """
        raise NotImplementedError

    async def stream(
        self,
        system: str,
        messages: list[dict],
        usage_out: list,
        *,
        dynamic_system: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Streaming completion.

        Yields plain text chunks. When the stream is exhausted, appends
        tokens_used (int or None) to usage_out so callers can retrieve it
        after the async-for loop.

        dynamic_system: per-request context appended after the cached static prompt.
        """
        raise NotImplementedError
        # Make Python recognise this as an async generator in subclasses:
        yield  # type: ignore[misc]


# ── OpenAI provider ────────────────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    """Wraps AsyncOpenAI. Used for structured tasks (mood insight, journal reflection)."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def _client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self._api_key)

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        *,
        dynamic_system: str = "",
    ) -> tuple[str, Optional[int]]:
        combined = system + ("\n\n" + dynamic_system if dynamic_system else "")
        full_messages = [{"role": "system", "content": combined}, *messages]
        completion = await self._client().chat.completions.create(
            model=self._model,
            messages=full_messages,  # type: ignore[arg-type]
            stream=False,
        )
        content = completion.choices[0].message.content or ""
        tokens: Optional[int] = (
            completion.usage.total_tokens if completion.usage else None
        )
        return content, tokens

    async def stream(
        self,
        system: str,
        messages: list[dict],
        usage_out: list,
        *,
        dynamic_system: str = "",
    ) -> AsyncGenerator[str, None]:
        combined = system + ("\n\n" + dynamic_system if dynamic_system else "")
        full_messages = [{"role": "system", "content": combined}, *messages]
        raw_stream = await self._client().chat.completions.create(
            model=self._model,
            messages=full_messages,  # type: ignore[arg-type]
            stream=True,
            stream_options={"include_usage": True},
        )
        tokens: Optional[int] = None
        async for chunk in raw_stream:
            if chunk.usage:
                tokens = chunk.usage.total_tokens
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        usage_out.append(tokens)


# ── Anthropic provider ─────────────────────────────────────────────────────────

# Tokens reserved for the visible output when thinking is active.
# max_tokens sent to the API = thinking_budget + _THINKING_OUTPUT_BUFFER.
_THINKING_OUTPUT_BUFFER = 1024


class AnthropicProvider(LLMProvider):
    """
    Wraps AsyncAnthropic.

    Used for main chat (empathy-focused) and insight/reflection generation.
    Optionally enables extended thinking for deeper, more nuanced outputs.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        thinking: bool = False,
        thinking_budget: int = 2000,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._thinking = thinking
        self._thinking_budget = thinking_budget

    def _client(self) -> AsyncAnthropic:
        return AsyncAnthropic(api_key=self._api_key)

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        *,
        dynamic_system: str = "",
    ) -> tuple[str, Optional[int]]:
        system_blocks = _system_blocks(system, dynamic_system)
        if self._thinking:
            # max_tokens must exceed budget_tokens; we add a buffer for the reply.
            effective_max = self._thinking_budget + _THINKING_OUTPUT_BUFFER
            response = await self._client().messages.create(
                model=self._model,
                max_tokens=effective_max,
                thinking={"type": "enabled", "budget_tokens": self._thinking_budget},
                system=system_blocks,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
                extra_headers=_CACHE_BETA_HEADER,
            )
            # Filter out thinking blocks — return only the visible text.
            content = ""
            for block in response.content:
                if block.type == "text":
                    content = block.text
                    break
        else:
            response = await self._client().messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=_INSIGHT_TEMPERATURE,
                system=system_blocks,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
                extra_headers=_CACHE_BETA_HEADER,
            )
            content = response.content[0].text if response.content else ""

        tokens: Optional[int] = None
        if response.usage:
            tokens = response.usage.input_tokens + response.usage.output_tokens
        return content, tokens

    async def stream(
        self,
        system: str,
        messages: list[dict],
        usage_out: list,
        *,
        dynamic_system: str = "",
    ) -> AsyncGenerator[str, None]:
        async with self._client().messages.stream(
            model=self._model,
            max_tokens=_CHAT_STREAM_MAX_TOKENS,
            system=_system_blocks(system, dynamic_system),  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
            extra_headers=_CACHE_BETA_HEADER,
        ) as s:
            async for text in s.text_stream:
                yield text
            # Capture usage after text_stream exhausted (still inside context)
            try:
                final = s.get_final_message()
                if final.usage:
                    usage_out.append(
                        final.usage.input_tokens + final.usage.output_tokens
                    )
                else:
                    usage_out.append(None)
            except Exception as exc:
                logger.debug("Could not retrieve Anthropic usage: %s", exc)
                usage_out.append(None)


# ── Fallback provider with circuit breaker ────────────────────────────────────

class FallbackProvider(LLMProvider):
    """
    Wraps a primary provider and a fallback provider behind a circuit breaker.

    Behaviour
    ---------
    - If the breaker is open, the primary is skipped and the fallback runs
      immediately.
    - Otherwise the primary is attempted. On exception, the failure is recorded
      and the fallback is invoked transparently.
    - Streaming: if the primary fails BEFORE yielding any chunk, the fallback
      stream is used. If it fails MID-stream, the partial text already sent to
      the client cannot be retracted; we re-raise so the caller's outer try
      block surfaces the error to the user (consistent with current SSE
      protocol). This keeps user-visible behaviour predictable.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        *,
        dynamic_system: str = "",
    ) -> tuple[str, Optional[int]]:
        if _cb_is_open():
            logger.info("Circuit breaker open — using fallback provider for complete()")
            return await self._fallback.complete(
                system, messages, max_tokens, dynamic_system=dynamic_system
            )
        try:
            return await self._primary.complete(
                system, messages, max_tokens, dynamic_system=dynamic_system
            )
        except Exception as exc:
            _cb_record_failure()
            logger.warning(
                "Primary LLM failed in complete(); falling back: %s", exc
            )
            return await self._fallback.complete(
                system, messages, max_tokens, dynamic_system=dynamic_system
            )

    async def stream(
        self,
        system: str,
        messages: list[dict],
        usage_out: list,
        *,
        dynamic_system: str = "",
    ) -> AsyncGenerator[str, None]:
        if _cb_is_open():
            logger.info("Circuit breaker open — using fallback provider for stream()")
            async for chunk in self._fallback.stream(
                system, messages, usage_out, dynamic_system=dynamic_system
            ):
                yield chunk
            return

        # We must detect failure BEFORE the first chunk to fall back transparently.
        # Once any byte has been yielded to the SSE consumer, mid-stream switching
        # would corrupt the user-visible reply, so we re-raise instead.
        primary_iter = self._primary.stream(
            system, messages, usage_out, dynamic_system=dynamic_system
        )
        first_chunk: Optional[str] = None
        try:
            first_chunk = await primary_iter.__anext__()
        except StopAsyncIteration:
            # Primary returned no chunks at all — treat as success (empty reply).
            return
        except Exception as exc:
            _cb_record_failure()
            logger.warning(
                "Primary LLM failed before first chunk in stream(); falling back: %s",
                exc,
            )
            async for chunk in self._fallback.stream(
                system, messages, usage_out, dynamic_system=dynamic_system
            ):
                yield chunk
            return

        # First chunk received from primary — commit to it.
        yield first_chunk
        try:
            async for chunk in primary_iter:
                yield chunk
        except Exception as exc:
            # Mid-stream failure: record it, but re-raise — the outer SSE
            # handler in chat_service emits an "error" frame to the client.
            _cb_record_failure()
            logger.error(
                "Primary LLM failed mid-stream; cannot fall back transparently: %s",
                exc,
            )
            raise


# ── Factories ──────────────────────────────────────────────────────────────────

def get_chat_provider() -> LLMProvider:
    """
    Return the chat provider with circuit breaker.

    Primary: Anthropic Claude Haiku (high empathy, prompt caching).
    Fallback: OpenAI gpt-4.1-mini (used when Anthropic is unavailable).

    The breaker trips after 3 consecutive failures within 60s and resets
    after 120s. See module-level circuit-breaker docs.
    """
    a_cfg = settings.anthropic_config
    o_cfg = settings.openai_config
    primary = AnthropicProvider(api_key=a_cfg["api_key"], model=a_cfg["chat_model"])
    fallback = OpenAIProvider(api_key=o_cfg["api_key"], model="gpt-4.1-mini")
    return FallbackProvider(primary=primary, fallback=fallback)


def get_crisis_chat_provider() -> LLMProvider:
    """Return a higher-capability provider for HIGH/CRITICAL crisis responses (Claude Sonnet)."""
    cfg = settings.anthropic_config
    model = cfg.get("crisis_model", "claude-sonnet-4-6")
    return AnthropicProvider(api_key=cfg["api_key"], model=model)


def get_insight_provider() -> LLMProvider:
    """
    Return the provider for mood insights and journal reflections.

    Uses Claude Haiku with extended thinking for deeper, more nuanced outputs
    while keeping the same safety and PT-BR quality guarantees as the chat model.
    thinking_budget=2000 balances quality vs. cost for short insight texts.

    Callers should pass max_tokens=_INSIGHT_MAX_TOKENS (800) to complete().
    When thinking=True the effective max is thinking_budget + _THINKING_OUTPUT_BUFFER
    and the max_tokens argument is ignored in favour of that calculation.
    """
    cfg = settings.anthropic_config
    return AnthropicProvider(
        api_key=cfg["api_key"],
        model=cfg.get("insight_model", "claude-haiku-4-5-20251001"),
        thinking=True,
        thinking_budget=2000,
    )
