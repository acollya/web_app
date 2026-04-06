"""
LLM Provider abstraction — unified interface over OpenAI and Anthropic.

Design
------
Two concrete providers are offered:

  OpenAIProvider   — wraps AsyncOpenAI (used for mood insights & journal reflections)
  AnthropicProvider — wraps AsyncAnthropic (used for main chat, empathy-focused)

Both expose the same two methods:

  complete(system, messages, max_tokens) -> (content, tokens_used)
      Non-streaming call. Returns the full reply plus total token count.

  stream(system, messages, usage_out) -> AsyncGenerator[str, None]
      Streaming call. Yields text chunks. Appends tokens_used to usage_out
      when the stream finishes, so the caller can read it after exhausting
      the generator.

Factory helpers
---------------
  get_chat_provider()    -> AnthropicProvider  (Claude Haiku)
  get_insight_provider() -> OpenAIProvider     (GPT-4.1-mini)

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

_DEFAULT_MAX_TOKENS = 1024


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

class AnthropicProvider(LLMProvider):
    """Wraps AsyncAnthropic. Used for main chat (empathy-focused, human-like tone)."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def _client(self) -> AsyncAnthropic:
        return AsyncAnthropic(api_key=self._api_key)

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> tuple[str, Optional[int]]:
        response = await self._client().messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,  # type: ignore[arg-type]
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
            max_tokens=_DEFAULT_MAX_TOKENS,
            system=system,
            messages=messages,  # type: ignore[arg-type]
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
    """Return the provider for main chat sessions (Anthropic Claude Haiku)."""
    cfg = settings.anthropic_config
    return AnthropicProvider(api_key=cfg["api_key"], model=cfg["chat_model"])


def get_insight_provider() -> LLMProvider:
    """Return the provider for mood insights and journal reflections (OpenAI GPT-4.1-mini)."""
    cfg = settings.openai_config
    return OpenAIProvider(
        api_key=cfg["api_key"],
        model=cfg.get("insight_model", "gpt-4.1-mini"),
    )
