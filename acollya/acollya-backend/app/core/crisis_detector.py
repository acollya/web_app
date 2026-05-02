"""
Crisis detection for PT-BR mental health conversations — 3-layer ensemble.

Layer 1 — regex fast-path (sync, zero latency):
    Scans for explicit crisis language. Returns immediately on HIGH.
    CRITICAL cases are validated by Layer 3 to reduce false positives.

Layer 2 — Haiku LLM classifier (async):
    Called when regex returns NONE or MEDIUM. Catches semantic equivalents,
    indirect expressions, and paraphrases that fixed patterns cannot cover.

Layer 3 — Sonnet confirmation (async):
    Called when any source produces CRITICAL. Provides a second clinical
    opinion before activating the highest-severity protocol.
    Fail-safe: keeps CRITICAL if the Sonnet call fails — a network error
    must never silently suppress a genuine crisis signal.

Severity levels:
  CRITICAL - Active suicidal/self-harm ideation, immediate risk
  HIGH     - Passive suicidal ideation, hopelessness, recent self-harm
  MEDIUM   - Significant distress, mentions of wanting to die in past tense
  NONE     - No crisis indicators detected

Protocol on CRITICAL/HIGH:
  - The chat service appends a CVV 188 resource block to the AI response
  - The frontend shows a crisis resource banner

CVV 188 is the Centro de Valorização da Vida, Brazil's 24/7 crisis line.

Usage (sync fast-path):
    result = detect_crisis(user_message)

Usage (full 3-layer ensemble):
    result = await detect_crisis_enhanced(user_message)
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CrisisLevel(str, Enum):
    NONE = "none"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CrisisDetectionResult:
    level: CrisisLevel
    matched_keywords: list[str]
    should_show_cvv: bool


# ── Keyword lists (PT-BR) ──────────────────────────────────────────────────────

_CRITICAL_PATTERNS = [
    r"\bvou me matar\b",
    r"\bquero me matar\b",
    r"\bvou me suicidar\b",
    r"\bquero me suicidar\b",
    r"\bvou tirar minha vida\b",
    r"\bquero tirar minha vida\b",
    r"\bvou me enforcar\b",
    r"\bvou tomar rem[eé]dio[s]? pra morrer\b",
    r"\bvou me jogar\b",
    r"\bme cortar hoje\b",
    r"\bjá decidi morrer\b",
    r"\bjá decidi acabar com tudo\b",
    r"\bnão quero mais viver\b",
    r"\bpreciso morrer\b",
    r"\bvou acabar com minha vida\b",
    r"\bestou me cortando\b",
    r"\bme machuquei agora\b",
]

_HIGH_PATTERNS = [
    r"\bpenso em suic[íi]dio\b",
    r"\bpensamento suicida\b",
    r"\bpensamentos de morte\b",
    r"\bpenso em me matar\b",
    r"\bpenso em morrer\b",
    r"\bme machuquei\b",
    r"\bme cortei\b",
    r"\bautomutilaç[aã]o\b",
    r"\bautomutilei\b",
    r"\bnão tenho motivo pra viver\b",
    r"\bnão vejo sentido em viver\b",
    r"\btudo seria melhor sem mim\b",
    r"\bseria melhor se eu n[ãa]o existisse\b",
    r"\bquero desaparecer para sempre\b",
    r"\bsinto que sou um peso\b",
    r"\bninguém sentiria minha falta\b",
]

_MEDIUM_PATTERNS = [
    r"\bqueria ter morrido\b",
    r"\bdevia ter morrido\b",
    r"\bdeveria n[ãa]o ter nascido\b",
    r"\bn[ãa]o quero mais estar aqui\b",
    r"\bcansado de viver\b",
    r"\bcansada de viver\b",
    r"\bvida n[ãa]o vale a pena\b",
    r"\bdesejo morrer\b",
    r"\bquero sumir\b",
    r"\bquero dormir e n[ãa]o acordar\b",
    r"\bn[ãa]o aguento mais\b",
    r"\bexausta de tudo\b",
    r"\bexausto de tudo\b",
    r"\btotalmente desesperado\b",
    r"\btotalmente desesperada\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_CRITICAL_COMPILED = _compile(_CRITICAL_PATTERNS)
_HIGH_COMPILED = _compile(_HIGH_PATTERNS)
_MEDIUM_COMPILED = _compile(_MEDIUM_PATTERNS)


def detect_crisis(text: str) -> CrisisDetectionResult:
    """
    Sync regex fast-path. Zero latency, no I/O.

    For full 3-layer detection (catches indirect/semantic expressions),
    use detect_crisis_enhanced() instead.
    """
    matched: list[str] = []

    for pattern in _CRITICAL_COMPILED:
        if pattern.search(text):
            matched.append(pattern.pattern)

    if matched:
        return CrisisDetectionResult(
            level=CrisisLevel.CRITICAL,
            matched_keywords=matched,
            should_show_cvv=True,
        )

    for pattern in _HIGH_COMPILED:
        if pattern.search(text):
            matched.append(pattern.pattern)

    if matched:
        return CrisisDetectionResult(
            level=CrisisLevel.HIGH,
            matched_keywords=matched,
            should_show_cvv=True,
        )

    for pattern in _MEDIUM_COMPILED:
        if pattern.search(text):
            matched.append(pattern.pattern)

    if matched:
        return CrisisDetectionResult(
            level=CrisisLevel.MEDIUM,
            matched_keywords=matched,
            should_show_cvv=True,
        )

    return CrisisDetectionResult(
        level=CrisisLevel.NONE,
        matched_keywords=[],
        should_show_cvv=False,
    )


# ── LLM layers ─────────────────────────────────────────────────────────────────

_CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"
_CONFIRMATION_MODEL = "claude-sonnet-4-6"

_CLASSIFY_SYSTEM = (
    "Você é um classificador de risco clínico para saúde mental em português do Brasil. "
    "Responda sempre com uma única palavra em minúsculas: none, medium, high ou critical."
)

_CLASSIFY_USER = (
    "Classifique o nível de risco da mensagem abaixo.\n\n"
    "Níveis:\n"
    "- none: sem sinais de crise ou sofrimento relevante\n"
    "- medium: sofrimento emocional significativo, sem risco imediato de autolesão\n"
    "- high: ideação suicida passiva, desejo de morte, autolesão mencionada, desesperança intensa\n"
    "- critical: plano ativo de suicídio, ato de autolesão em curso, emergência imediata\n\n"
    'Mensagem: "{text}"\n\n'
    "Responda com uma única palavra (none/medium/high/critical):"
)

_CONFIRM_USER = (
    "Analise se a mensagem indica risco CRÍTICO imediato — plano ativo de suicídio, "
    "intenção declarada de autolesão grave, ou emergência em curso.\n\n"
    'Mensagem: "{text}"\n\n'
    "Responda apenas SIM (risco crítico confirmado) ou NÃO:"
)

_LEVELS_ORDER = [CrisisLevel.NONE, CrisisLevel.MEDIUM, CrisisLevel.HIGH, CrisisLevel.CRITICAL]


async def _classify_with_haiku(text: str) -> CrisisLevel:
    """Layer 2: classify crisis level with Claude Haiku."""
    try:
        from anthropic import AsyncAnthropic  # noqa: PLC0415 — lazy to avoid circular import
        from app.config import settings

        cfg = settings.anthropic_config
        client = AsyncAnthropic(api_key=cfg["api_key"])
        response = await client.messages.create(
            model=_CLASSIFIER_MODEL,
            max_tokens=8,
            system=_CLASSIFY_SYSTEM,
            messages=[{"role": "user", "content": _CLASSIFY_USER.format(text=text[:500])}],
        )
        raw = response.content[0].text.strip().lower() if response.content else "none"
        word = raw.split()[0] if raw else "none"
        try:
            return CrisisLevel(word)
        except ValueError:
            for level in (CrisisLevel.CRITICAL, CrisisLevel.HIGH, CrisisLevel.MEDIUM):
                if level.value in raw:
                    return level
            return CrisisLevel.NONE
    except Exception as exc:
        logger.warning("Crisis classifier (Haiku) failed, using regex result: %s", exc)
        return CrisisLevel.NONE


async def _confirm_critical_with_sonnet(text: str) -> bool:
    """
    Layer 3: confirm CRITICAL with Claude Sonnet.

    Returns True (CRITICAL confirmed) on API failure — a network error
    must never silently suppress a genuine crisis.
    """
    try:
        from anthropic import AsyncAnthropic  # noqa: PLC0415 — lazy to avoid circular import
        from app.config import settings

        cfg = settings.anthropic_config
        client = AsyncAnthropic(api_key=cfg["api_key"])
        response = await client.messages.create(
            model=_CONFIRMATION_MODEL,
            max_tokens=8,
            messages=[{"role": "user", "content": _CONFIRM_USER.format(text=text[:500])}],
        )
        raw = response.content[0].text.strip().upper() if response.content else ""
        return raw.startswith("SIM")
    except Exception as exc:
        logger.warning("Crisis confirmation (Sonnet) failed, keeping CRITICAL: %s", exc)
        return True


async def detect_crisis_enhanced(text: str) -> CrisisDetectionResult:
    """
    3-layer ensemble crisis detection.

    Layer 1 — regex: returns immediately on HIGH (trusted). CRITICAL goes to Layer 3.
    Layer 2 — Haiku: called for NONE/MEDIUM to catch indirect expressions.
    Layer 3 — Sonnet: confirms any CRITICAL before activating highest protocol.
    """
    regex_result = detect_crisis(text)

    if regex_result.level == CrisisLevel.HIGH:
        return regex_result

    if regex_result.level == CrisisLevel.CRITICAL:
        confirmed = await _confirm_critical_with_sonnet(text)
        if confirmed:
            return regex_result
        return CrisisDetectionResult(
            level=CrisisLevel.HIGH,
            matched_keywords=regex_result.matched_keywords,
            should_show_cvv=True,
        )

    # NONE or MEDIUM: upgrade with Haiku
    llm_level = await _classify_with_haiku(text)
    regex_idx = _LEVELS_ORDER.index(regex_result.level)
    llm_idx = _LEVELS_ORDER.index(llm_level)
    candidate = _LEVELS_ORDER[max(regex_idx, llm_idx)]

    if candidate == CrisisLevel.CRITICAL:
        confirmed = await _confirm_critical_with_sonnet(text)
        if not confirmed:
            candidate = CrisisLevel.HIGH

    return CrisisDetectionResult(
        level=candidate,
        matched_keywords=regex_result.matched_keywords,
        should_show_cvv=candidate != CrisisLevel.NONE,
    )


# ── CVV response block ─────────────────────────────────────────────────────────

CVV_MESSAGE = (
    "\n\n---\n"
    "Percebi que você pode estar passando por um momento muito difícil. "
    "Você não precisa enfrentar isso sozinha.\n\n"
    "**CVV - Centro de Valorização da Vida**\n"
    "- Ligue **188** (24 horas, gratuito)\n"
    "- Chat: [cvv.org.br](https://www.cvv.org.br)\n\n"
    "Estou aqui para continuar conversando com você."
)
