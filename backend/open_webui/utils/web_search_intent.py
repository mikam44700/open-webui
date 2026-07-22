"""Fast, provider-agnostic gate for legacy web-search flows.

Native function-calling models decide themselves whether to invoke the web tools.
Legacy models need this deterministic gate so keeping web access enabled does not
add a query-generation LLM call (or consume search credits) on every chat turn.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class WebSearchDecision:
    should_search: bool
    reason: str


_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)

_OPT_OUT_PHRASES = (
    "sans internet",
    "sans le web",
    "sans recherche web",
    "sans rechercher",
    "sans chercher",
    "ne cherche pas",
    "ne recherche pas",
    "n utilise pas internet",
    "n utilise pas le web",
    "without internet",
    "without web search",
    "do not search",
    "dont search",
    "offline only",
)

_EXPLICIT_SEARCH_PHRASES = (
    "cherche sur internet",
    "recherche sur internet",
    "cherche sur le web",
    "recherche sur le web",
    "fais une recherche",
    "recherche en ligne",
    "verifie sur internet",
    "verifie en ligne",
    "trouve moi en ligne",
    "consulte le web",
    "parcours le web",
    "search the web",
    "search online",
    "look it up",
    "browse the web",
    "browse online",
    "check online",
)

_FRESHNESS_TERMS = (
    "actualite",
    "actualites",
    "aujourd hui",
    "en ce moment",
    "a l instant",
    "cette semaine",
    "ce mois ci",
    "dernieres nouvelles",
    "derniere version",
    "derniere mise a jour",
    "mise a jour disponible",
    "prix actuel",
    "tarif actuel",
    "cours actuel",
    "meteo",
    "score en direct",
    "resultats en direct",
    "news",
    "today",
    "right now",
    "currently",
    "this week",
    "this month",
    "latest",
    "newest",
    "current price",
    "current version",
    "weather",
    "live score",
)

_VERIFICATION_TERMS = (
    "avec les sources",
    "donne moi les sources",
    "cite tes sources",
    "sources et liens",
    "liens cliquables",
    "lien officiel",
    "source officielle",
    "verifie cette information",
    "est ce vrai",
    "fact check",
    "with sources",
    "cite sources",
    "official source",
    "official link",
    "verify this",
)

_LIVE_PRODUCT_TERMS = (
    "est disponible",
    "encore disponible",
    "disponible sur quel",
    "compatible avec",
    "quel abonnement",
    "quelle offre",
    "quel forfait",
    "conditions actuelles",
    "reglementation actuelle",
    "loi actuelle",
    "is available",
    "still available",
    "compatible with",
    "which subscription",
    "current plan",
    "current regulation",
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower().replace("’", " ").replace("'", " ").replace("-", " ")
    return " ".join(text.split())


def classify_web_search_intent(user_message: str | None) -> WebSearchDecision:
    """Return whether a legacy chat turn genuinely needs web access.

    The gate deliberately handles only high-confidence intents. Ambiguous stable
    questions remain direct and fast; the user can always explicitly request a
    search. Native tool-calling models do not use this function.
    """

    raw_message = (user_message or "").strip()
    if not raw_message:
        return WebSearchDecision(False, "empty")

    normalized_message = _normalize(raw_message)

    if any(phrase in normalized_message for phrase in _OPT_OUT_PHRASES):
        return WebSearchDecision(False, "user_opt_out")

    if _URL_RE.search(raw_message):
        return WebSearchDecision(True, "url")

    signal_groups = (
        ("explicit", _EXPLICIT_SEARCH_PHRASES),
        ("freshness", _FRESHNESS_TERMS),
        ("verification", _VERIFICATION_TERMS),
        ("live_product", _LIVE_PRODUCT_TERMS),
    )
    for reason, phrases in signal_groups:
        if any(phrase in normalized_message for phrase in phrases):
            return WebSearchDecision(True, reason)

    return WebSearchDecision(False, "stable_or_conversational")
