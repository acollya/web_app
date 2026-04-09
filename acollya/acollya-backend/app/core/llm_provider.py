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
  _INSIGHT_TEMPERATURE = 0.7  — aplicado em complete() quando thinking=False.
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
from typing import AsyncGenerator, Optional

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Chat streaming: respostas terapêuticas podem ser densas (acolhimento + orientação).
_CHAT_STREAM_MAX_TOKENS = 2000

# Insights e reflexões: texto curto e direto — 800 tokens é mais que suficiente.
_INSIGHT_MAX_TOKENS = 800

# Fallback para chamadas genéricas (complete() sem thinking via base class).
_DEFAULT_MAX_TOKENS = 1024

# Temperature para complete() sem thinking — reduz variância em contexto clínico.
_INSIGHT_TEMPERATURE = 0.7

# Anthropic prompt-caching beta header.
# Caches system prompt across turns of the same conversation.
# Requires ≥ 1024 tokens in the cached block; silently skipped if not met.
_CACHE_BETA_HEADER = {"anthropic-beta": "prompt-caching-2024-07-31"}


def _system_blocks(system: str) -> list[dict]:
    """Wraps the system string into a content block with cache_control."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


# ── Base class ─────────────────────────────────────────────────────────────────

class LLMProvider:
    """Duck-typed base. Subclasses must implement complete() and stream()."""

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> tuple[str, Optional[int]]:
        """
        Non-streaming completion.

        Parameters
        ----------
        system   : System prompt text.
        messages : Conversation turns — [{"role": "user"|"assistant", "content": "..."}].
                   Do NOT include a system-role dict here; pass it via `system`.
        max_tokens: Maximum tokens to generate.

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
    ) -> AsyncGenerator[str, None]:
        """
        Streaming completion.

        Yields plain text chunks. When the stream is exhausted, appends
        tokens_used (int or None) to usage_out so callers can retrieve it
        after the async-for loop.
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
    ) -> tuple[str, Optional[int]]:
        full_messages = [{"role": "system", "content": system}, *messages]
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
    ) -> AsyncGenerator[str, None]:
        full_messages = [{"role": "system", "content": system}, *messages]
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
    ) -> tuple[str, Optional[int]]:
        system_blocks = _system_blocks(system)
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
    ) -> AsyncGenerator[str, None]:
        async with self._client().messages.stream(
            model=self._model,
            max_tokens=_CHAT_STREAM_MAX_TOKENS,
            system=_system_blocks(system),  # type: ignore[arg-type]
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


# ── Factories ──────────────────────────────────────────────────────────────────

def get_chat_provider() -> LLMProvider:
    """Return the provider for main chat sessions (Claude Haiku, no thinking)."""
    cfg = settings.anthropic_config
    return AnthropicProvider(api_key=cfg["api_key"], model=cfg["chat_model"])


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
