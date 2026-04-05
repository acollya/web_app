"""
Crisis detection for PT-BR mental health conversations.

Severity levels:
  CRITICAL - Active suicidal/self-harm ideation, immediate risk
  HIGH     - Passive suicidal ideation, hopelessness, recent self-harm
  MEDIUM   - Significant distress, mentions of wanting to die in past tense

Protocol on CRITICAL/HIGH:
  - The chat service appends a CVV 188 resource block to the AI response
  - The frontend shows a crisis resource banner
  - (Future) A background task logs the event for clinical review

CVV 188 is the Centro de Valorização da Vida, Brazil's 24/7 crisis line.

Usage:
    result = detect_crisis(user_message)
    if result.level != CrisisLevel.NONE:
        # inject CVV message
"""
import re
from dataclasses import dataclass
from enum import Enum


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
# Patterns use word boundaries to reduce false positives.
# All patterns are compiled at module load time.

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
    Scan text for crisis indicators.

    Returns the highest severity level found and the matched keywords.
    Designed to run synchronously (no I/O) inside an async endpoint.
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


# ── CVV response block ─────────────────────────────────────────────────────────

CVV_MESSAGE = (
    "\n\n---\n"
    "Percebi que voce pode estar passando por um momento muito dificil. "
    "Voce nao precisa enfrentar isso sozinho(a).\n\n"
    "**CVV - Centro de Valorizacao da Vida**\n"
    "- Ligue **188** (24 horas, gratuito)\n"
    "- Chat: [cvv.org.br](https://www.cvv.org.br)\n\n"
    "Estou aqui para continuar conversando com voce."
)
