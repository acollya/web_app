"""
routing_service — classifica intenção do usuário antes do LLM principal.

Dois tipos de intenção:
  desabafar   — usuário quer ser ouvido e validado emocionalmente
  orientacao  — usuário quer orientação prática ou estruturada

A classificação usa uma chamada rápida ao Claude Haiku com max_tokens=5.
Em caso de erro retorna "desabafar" (mais seguro — prioriza acolhimento).

Integração no chat_service
--------------------------
    intent = await classify_intent(user_content)
    tone_modifier = get_tone_modifier(intent)
    static, dynamic, conversation = _build_conversation(
        history, user_content, persona_context, rag_context,
        rolling_summary, tone_modifier=tone_modifier,
    )

Notas
-----
- Latência adicional ~300ms; corre depois do crisis_detector síncrono e antes
  do LLM principal — soma-se ao critical-path do streaming SSE.
- Em caso de exceção, retorna sempre "desabafar" — escolher acolhimento por
  padrão é o caminho clinicamente mais seguro quando há incerteza.
- Truncamos a entrada em 500 caracteres para manter o classificador leve;
  500 chars é suficiente para inferir intenção em mensagens curtas típicas
  do chat terapêutico.
"""
import logging
from typing import Literal

from app.config import settings

logger = logging.getLogger(__name__)

IntentType = Literal["desabafar", "orientacao"]

_ROUTE_SYSTEM = (
    "Classify the following Portuguese message. "
    "Reply with exactly one word: 'desabafar' if the person wants emotional support/to vent, "
    "or 'orientacao' if they want practical guidance or structured advice. "
    "No other text."
)

_TONE_MODIFIERS: dict[IntentType, str] = {
    "desabafar": (
        "## Modo de escuta\n"
        "O usuário precisa ser ouvido. Priorize validação emocional e presença. "
        "Faça perguntas reflexivas abertas. Evite dar conselhos práticos nesta resposta, "
        "a menos que o usuário peça explicitamente."
    ),
    "orientacao": (
        "## Modo de orientação\n"
        "O usuário busca orientação prática. Ofereça estrutura clara: "
        "valide brevemente o contexto emocional e então apresente passos ou perspectivas concretas. "
        "Seja objetivo e organizado, mas mantenha o tom acolhedor."
    ),
}


async def classify_intent(text: str) -> IntentType:
    """Fast intent classification using Claude Haiku. Falls back to 'desabafar' on error."""
    from anthropic import AsyncAnthropic
    try:
        client = AsyncAnthropic(api_key=settings.anthropic_config["api_key"])
        response = await client.messages.create(
            model=settings.anthropic_config.get("chat_model", "claude-haiku-4-5-20251001"),
            max_tokens=5,
            system=_ROUTE_SYSTEM,
            messages=[{"role": "user", "content": text[:500]}],
        )
        result = response.content[0].text.strip().lower()
        if "orientacao" in result or "orientação" in result:
            return "orientacao"
        return "desabafar"
    except Exception as exc:
        logger.debug("Intent classification failed, defaulting to desabafar: %s", exc)
        return "desabafar"


def get_tone_modifier(intent: IntentType) -> str:
    """Return the dynamic-system prefix string for the given intent."""
    return _TONE_MODIFIERS[intent]
