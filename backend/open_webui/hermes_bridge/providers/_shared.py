"""Helpers de curation partagés par plusieurs modules ``providers/*.py``.

Zéro dépendance vers ``hermes_adapter`` (aucun import, même différé) : ce module est
une feuille de l'arbre d'imports, importée PAR ``hermes_adapter.py`` ET par les
modules ``providers/*.py`` — jamais l'inverse. C'est ce qui casse le cycle.
"""

from __future__ import annotations

import re

# =============================================================================
# Détection de crédit/solde : politique de sonde ASYMÉTRIQUE, PAR PROVIDER
# =============================================================================
# La sonde = un appel à un modèle payant (1 token). Coût réel : NUL sans crédit (la requête est
# rejetée 402/403 AVANT toute génération → rien de facturé) ; ~1 token une fois avec crédit.
# Politique (demandée par le client, pour ne jamais consommer inutilement) :
#   - crédit CONFIRMÉ (True) → on ne re-sonde JAMAIS ce provider (jusqu'à changement de sa clé) ;
#   - pas de crédit (False) → petite re-sonde toutes les _CREDIT_RECHECK_TTL (gratuite) pour
#     capter le paiement et retirer le badge vite. Chaque provider a son cache → indépendant.
_CREDIT_RECHECK_TTL = 180  # 3 min : re-sonde quand il n'y a PAS de crédit (sonde gratuite)


def _credit_cache_hit(cache_entry: dict | None, api_key: str, now: float) -> bool | None:
    """Applique la politique asymétrique à une entrée de cache {has, ts}. Renvoie la valeur
    mémorisée si elle est encore valable (True = définitif ; False = valable _CREDIT_RECHECK_TTL),
    sinon ``None`` (→ l'appelant doit (re)sonder)."""
    if not cache_entry:
        return None
    has = cache_entry.get("has")
    if has is True:
        return True  # crédit confirmé → jamais re-sondé
    if has is False and (now - cache_entry.get("ts", 0.0)) < _CREDIT_RECHECK_TTL:
        return False
    return None


# =============================================================================
# Affichage « pro » des modèles : libellés lisibles + ordre curé (récent → ancien)
# =============================================================================
# Les providers natifs exposent des IDs bruts (« claude-opus-4-8 », suffixe de date inclus).
# Pour le dirigeant non-tech on affiche un libellé propre : Majuscules, « . » entre versions
# (4-8 → 4.8), sans date. L'ID technique envoyé à l'API reste INCHANGÉ — seul le label change.
# Ordre curé par provider (récent → ancien ; Mistral = par puissance Large>Medium>Small). Le
# modèle recommandé (_RECOMMENDED_MODEL) est placé en tête. Un modèle non listé (nouveau) est
# ajouté À LA FIN avec un label auto-embelli — jamais masqué.
_MODEL_DATE_SUFFIX = re.compile(r"-\d{6,8}$")


def _beautify_model_label(model_id: str) -> str:
    """Rend un ID de modèle lisible : Majuscules, « . » entre versions, sans suffixe de date.
    Filet pour les providers/modèles non curés (ne remplace jamais un label curé explicite)."""
    s = _MODEL_DATE_SUFFIX.sub("", model_id).replace(":", "-")
    out: list[str] = []
    for part in s.split("-"):
        if not part:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", part) and out and re.search(r"\d$", out[-1]):
            out[-1] = f"{out[-1]}.{part}"  # fusionne les segments de version (4-8 → 4.8)
        elif re.fullmatch(r"\d+[bkmBKM]", part):
            out.append(part[:-1] + part[-1].upper())  # taille : 120b → 120B
        else:
            out.append(part[:1].upper() + part[1:])
    return "-".join(out)


# Tables curées (ordre + label affiché) pour les fournisseurs testés. Ordre = récent → ancien
# (Mistral = par puissance). L'auto-activation reste pilotée par _RECOMMENDED_MODEL, pas par
# l'ordre d'affichage — le 1er de la liste n'est donc pas forcément le défaut du chat.
# Cohere : liste FIGÉE, validée par test réel (2026-07-07, clé du client). Les fallback_models
# du plugin (command-a-03-2025, command-r-plus, command-r) sont PÉRIMÉS : Cohere a supprimé
# `command-r` ET `command-r-plus` le 2026-09-15 (HTTP « model was removed ») → 2 des 3 modèles
# proposés plantaient. On expose donc uniquement les modèles réellement servis par /models
# (endpoint natif, authed), généralistes command-a / command-r, ordre récent → ancien. Les
# variantes de niche (translate, arabic, aya, tiny-aya, north-mini-code) sont écartées pour ne
# pas noyer le dirigeant. À revalider si Cohere fait évoluer son catalogue. Zéro modif moteur.
_COHERE_CURATED_MODELS: list[tuple[str, str]] = [
    ("command-a-plus-05-2026", "Command-A-Plus"),
    ("command-a-reasoning-08-2025", "Command-A-Reasoning"),
    ("command-a-vision-07-2025", "Command-A-Vision"),
    ("command-a-03-2025", "Command-A"),
    ("command-r7b-12-2024", "Command-R7B"),
    ("command-r-plus-08-2024", "Command-R-Plus"),
    ("command-r-08-2024", "Command-R"),
]


_CURATED_MODELS: dict[str, list[tuple[str, str]]] = {
    "anthropic": [  # plus puissant/récent → ancien (Fable 5 = génération la plus récente)
        ("claude-fable-5", "Claude-Fable-5"),
        ("claude-opus-4-8", "Claude-Opus-4.8"),
        ("claude-opus-4-7", "Claude-Opus-4.7"),
        ("claude-opus-4-6", "Claude-Opus-4.6"),
        ("claude-sonnet-4-6", "Claude-Sonnet-4.6"),
        ("claude-opus-4-5-20251101", "Claude-Opus-4.5"),
        ("claude-sonnet-4-5-20250929", "Claude-Sonnet-4.5"),
        ("claude-haiku-4-5-20251001", "Claude-Haiku-4.5"),
        ("claude-opus-4-20250514", "Claude-Opus-4"),
        ("claude-sonnet-4-20250514", "Claude-Sonnet-4"),
    ],
    "gemini": [
        ("gemini-3.5-flash", "Gemini-3.5-Flash"),
        ("gemini-3.1-pro-preview", "Gemini-3.1-Pro-Preview"),
        ("gemini-3.1-flash-lite-preview", "Gemini-3.1-Flash-Lite-Preview"),
        ("gemini-3-pro-preview", "Gemini-3-Pro-Preview"),
    ],
    "deepseek": [
        ("deepseek-v4-pro", "Deepseek-V4-Pro"),
        ("deepseek-v4-flash", "Deepseek-V4-Flash"),
        ("deepseek-reasoner", "Deepseek-Reasoner"),
        ("deepseek-chat", "Deepseek-Chat"),
    ],
    "xai": [
        ("grok-4.3", "Grok-4.3"),
        ("grok-4.20-0309-reasoning", "Grok-4.20-Reasoning"),
        ("grok-4.20-0309-non-reasoning", "Grok-4.20-Non-Reasoning"),
        ("grok-4.20-multi-agent-0309", "Grok-4.20-Multi-Agent"),
        ("grok-composer-2.5-fast", "Grok-Composer-2.5-Fast"),
        ("grok-build-0.1", "Grok-Build-0.1"),
        ("grok-imagine-image", "Grok-Imagine-Image"),
        ("grok-imagine-image-quality", "Grok-Imagine-Image-Quality"),
        ("grok-imagine-video", "Grok-Imagine-Video"),
    ],
    "mistral": [  # par puissance : Large > Medium > Small
        ("mistral-large-latest", "Mistral-Large-Latest"),
        ("magistral-medium-latest", "Magistral-Medium-Latest"),
        ("mistral-small-latest", "Mistral-Small-Latest"),
    ],
    "kimi-coding": [  # ordre produit vérifié : plus récent → plus ancien (2026-07-22)
        # Les deux API Kimi n'exposent pas toujours les mêmes alias. La fonction
        # `_display_pairs` ne conserve que les IDs réellement renvoyés par la clé : cette
        # table nettoie donc les libellés et l'ordre sans inventer de disponibilité.
        ("kimi-k3", "Kimi K3"),
        ("k3", "Kimi K3"),
        ("kimi-for-coding-highspeed", "Kimi K2.7 Code HighSpeed"),
        ("kimi-k2.7-code-highspeed", "Kimi K2.7 Code HighSpeed"),
        # ID de requête officiel Kimi Code. `kimi-k2.7-code` est seulement un nom de
        # version parfois renvoyé par `/models` et provoque HTTP 401 au chat.
        ("kimi-for-coding", "Kimi K2.7 Code"),
        ("kimi-k2.7-code", "Kimi K2.7 Code"),
        ("kimi-k2.6", "Kimi K2.6"),
        ("kimi-k2.5", "Kimi K2.5"),
        ("kimi-k2-thinking-turbo", "Kimi K2 Thinking Turbo"),
        ("kimi-k2-thinking", "Kimi K2 Thinking"),
        ("kimi-k2-0905-preview", "Kimi K2 0905 Preview"),
        ("kimi-k2-turbo-preview", "Kimi K2 Turbo Preview"),
        ("moonshot-v1-auto", "Moonshot-V1-Auto"),
        ("moonshot-v1-128k", "Moonshot-V1-128K"),
        ("moonshot-v1-32k", "Moonshot-V1-32K"),
        ("moonshot-v1-8k", "Moonshot-V1-8K"),
        ("moonshot-v1-128k-vision-preview", "Moonshot-V1-128K-Vision"),
        ("moonshot-v1-32k-vision-preview", "Moonshot-V1-32K-Vision"),
        ("moonshot-v1-8k-vision-preview", "Moonshot-V1-8K-Vision"),
    ],
    "minimax-oauth": [  # Compte/OAuth (Token Plan) : M2.7-highspeed placé avant M2.7 (choix produit)
        ("MiniMax-M3", "MiniMax-M3"),
        ("MiniMax-M2.7-highspeed", "MiniMax-M2.7-Highspeed"),
        ("MiniMax-M2.7", "MiniMax-M2.7"),
    ],
    "cerebras": [  # catalogue OFFICIEL COMPLET = 3 modèles (testés en réel 2026-07-08, TOUS
        # tool-capable, TOUS gratuits : 1M tokens/j, 30 req/min). Cerebras garde volontairement
        # peu de modèles (chacun optimisé pour la puce WSE → ultra-rapide). Ordre : Production
        # (stable) d'abord, puis Preview (« éval seulement, peut être retiré vite » selon la doc
        # Cerebras) → le catalogue LIVE (`_cerebras_model_pairs`) retire tout seul un Preview
        # discontinué. IDs classiques (llama*/qwen*/deepseek*) tous en 404 → écartés.
        ("gpt-oss-120b", "Gpt-Oss-120B"),  # Production (stable) — recommandé
        ("gemma-4-31b", "Gemma-4-31B"),  # Preview
        ("zai-glm-4.7", "Zai-Glm-4.7"),  # Preview
    ],
    "fireworks": [  # catalogue LIVE curé (testé en réel 2026-07-08, clé client). IDs au format
        # COMPLET `accounts/fireworks/models/…` exigé par le plugin/moteur. ORDRE ALPHABÉTIQUE.
        # 7 exposés → 5 gardés : flux-1-schnell (image, pas chat) et kimi-k2p5 (HTTP 500 constant)
        # écartés. Les fallback_models du plugin (llama-v3p3-70b, deepseek-v3) sont PÉRIMÉS (404).
        # Libellés : « p » = point de version (glm-5p1 → Glm-5.1).
        ("accounts/fireworks/models/deepseek-v4-pro", "Deepseek-V4-Pro"),  # 1M ctx — recommandé
        ("accounts/fireworks/models/glm-5p1", "Glm-5.1"),
        ("accounts/fireworks/models/glm-5p2", "Glm-5.2"),
        ("accounts/fireworks/models/gpt-oss-120b", "Gpt-Oss-120B"),
        ("accounts/fireworks/models/kimi-k2p6", "Kimi-K2.6"),  # vision
    ],
    "groq": [  # catalogue LIVE curé (17 exposés → 7 gardés, testés en réel 2026-07-08, clé client).
        # TOUS tool-capable prouvés (POST /chat/completions avec tool → tool_calls). Écartés : STT
        # (whisper×2), TTS (orpheus×2), garde/modération (prompt-guard×2, gpt-oss-safeguard), allam
        # (arabe, ctx 4k) et groq/compound* (agentiques à outils intégrés → refusent le tool calling
        # externe, HTTP 400). Tier gratuit généreux → tout gratuit. Ordre : recommandé (llama-3.3
        # versatile, stable) d'abord, puis raisonneurs (gpt-oss/qwen3), puis vision (scout) et rapide.
        ("llama-3.3-70b-versatile", "Llama-3.3-70B"),  # flagship stable, tool-capable — recommandé
        ("openai/gpt-oss-120b", "GPT-OSS-120B"),  # raisonne (reasoning_effort honoré)
        ("openai/gpt-oss-20b", "GPT-OSS-20B"),  # raisonne
        ("qwen/qwen3.6-27b", "Qwen3.6-27B"),  # raisonne
        ("qwen/qwen3-32b", "Qwen3-32B"),  # raisonne
        ("meta-llama/llama-4-scout-17b-16e-instruct", "Llama-4-Scout-17B"),  # vision
        ("llama-3.1-8b-instant", "Llama-3.1-8B"),  # rapide
    ],
    "xiaomi": [  # catalogue LIVE curé (testé en réel 2026-07-08, clé client). `GET /v1/models`
        # (authed → test de clé fiable, 200) renvoie 6 IDs dont 4 NON-chat écartés : `-asr`
        # (reconnaissance vocale) et `-tts`/`-tts-voiceclone`/`-tts-voicedesign` (synthèse vocale) →
        # tous « Param Incorrect » (400) sur /chat/completions. Restent les 2 vrais LLM, TOUS
        # tool-capable + raisonnants prouvés (reasoning_content réel, POST tool → tool_calls). La
        # liste FIGÉE du moteur exposait en plus `mimo-v2-pro`/`mimo-v2-omni`/`mimo-v2-flash`
        # (génération v2 PÉRIMÉE → « Unsupported model » 400) : le live les retire tout seuls.
        # Libellés « MiMo » (branding Xiaomi, sinon _beautify donnerait « Mimo »). Recommandé = Pro.
        ("mimo-v2.5-pro", "MiMo-V2.5-Pro"),  # le plus puissant — recommandé
        ("mimo-v2.5", "MiMo-V2.5"),
    ],
    "stepfun": [  # catalogue LIVE curé (endpoint direct api.stepfun.ai/step_plan). `GET /models`
        # (authed → 200 même sans abonnement) renvoie `step-3.5-flash` + son snapshot daté
        # `step-3.5-flash-2603` (écarté : doublon). NON testé E2E — le chat exige un forfait Step
        # Plan payant (choix client : pas d'abonnement, 2026-07-08). Capacités = specs officielles.
        ("step-3.5-flash", "Step-3.5-Flash"),  # MoE 196.8B, raisonne (AIME 99.8%), 256K — recommandé
    ],
}


def _display_pairs(slug: str, raw_ids: list[str]) -> list[tuple[str, str]]:
    """(id, label) pour le sélecteur : ordre + libellés curés si le provider est connu,
    sinon libellés auto-embellis. Ne montre que les modèles réellement exposés par le moteur ;
    un modèle inconnu de la table (nouveau) passe à la fin, label auto-embelli."""
    # Les régions internationale et chinoise de Kimi servent la même famille de
    # modèles : elles partagent donc les mêmes libellés et le même ordre produit.
    curated_slug = "kimi-coding" if slug == "kimi-coding-cn" else slug
    curated = _CURATED_MODELS.get(curated_slug)
    if not curated:
        return [(mid, _beautify_model_label(mid)) for mid in raw_ids]
    order = {mid: i for i, (mid, _lbl) in enumerate(curated)}
    labels = {mid: lbl for mid, lbl in curated}
    known = sorted((m for m in raw_ids if m in order), key=lambda m: order[m])
    unknown = [m for m in raw_ids if m not in order]
    return [(m, labels[m]) for m in known] + [(m, _beautify_model_label(m)) for m in unknown]


# NVIDIA NIM : liste FIGÉE, validée par test réel (2026-07-06). Le catalogue /models de
# NVIDIA est truffé de « fantômes » (modèles listés mais non servis pour un compte free →
# 404 « not found for account » ou timeout > 40 s), et les fallback_models du profil moteur
# sont partiellement périmés. On expose donc uniquement les modèles réellement appelables ET
# compatibles tool calling (indispensable au chat agentique), grands noms en tête. Zéro
# fantôme, zéro modèle qui plante. À revalider périodiquement (la dispo NVIDIA dépend du
# compte/moment). Test : requête chat + tools sur chaque modèle → 200 = gardé.
_NVIDIA_CURATED_MODELS: list[tuple[str, str]] = [
    ("nvidia/nemotron-3-super-120b-a12b", "NVIDIA: Nemotron 3 Super 120B"),
    ("nvidia/nemotron-3-ultra-550b-a55b", "NVIDIA: Nemotron 3 Ultra 550B"),
    ("nvidia/nemotron-3-nano-30b-a3b", "NVIDIA: Nemotron 3 Nano 30B"),
    ("nvidia/nvidia-nemotron-nano-9b-v2", "NVIDIA: Nemotron Nano 9B v2"),
    ("meta/llama-4-maverick-17b-128e-instruct", "Meta: Llama 4 Maverick 17B"),
    ("meta/llama-3.1-70b-instruct", "Meta: Llama 3.1 70B"),
    ("meta/llama-3.1-8b-instruct", "Meta: Llama 3.1 8B"),
    ("mistralai/mistral-large-3-675b-instruct-2512", "Mistral: Large 3 675B"),
    ("mistralai/mistral-medium-3.5-128b", "Mistral: Medium 3.5 128B"),
    ("mistralai/mistral-small-4-119b-2603", "Mistral: Small 4 119B"),
    ("mistralai/ministral-14b-instruct-2512", "Mistral: Ministral 14B"),
    ("mistralai/mistral-nemotron", "Mistral: Mistral Nemotron"),
    ("qwen/qwen3.5-122b-a10b", "Qwen: Qwen 3.5 122B"),
    ("qwen/qwen3-next-80b-a3b-instruct", "Qwen: Qwen3-Next 80B"),
    ("deepseek-ai/deepseek-v4-flash", "DeepSeek: V4 Flash"),
    ("moonshotai/kimi-k2.6", "Moonshot: Kimi K2.6"),
    ("minimaxai/minimax-m3", "MiniMax: M3"),
    ("minimaxai/minimax-m2.7", "MiniMax: M2.7"),
    ("openai/gpt-oss-120b", "OpenAI: gpt-oss 120B"),
    ("openai/gpt-oss-20b", "OpenAI: gpt-oss 20B"),
    ("google/gemma-4-31b-it", "Google: Gemma 4 31B"),
    ("microsoft/phi-4-multimodal-instruct", "Microsoft: Phi-4 Multimodal"),
    ("nvidia/llama-3.3-nemotron-super-49b-v1.5", "NVIDIA: Llama 3.3 Nemotron Super 49B v1.5"),
    ("nvidia/llama-3.3-nemotron-super-49b-v1", "NVIDIA: Llama 3.3 Nemotron Super 49B v1"),
    ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "NVIDIA: Nemotron 3 Nano Omni 30B (raisonnement)"),
    ("nvidia/nemotron-nano-12b-v2-vl", "NVIDIA: Nemotron Nano 12B VL"),
    ("nvidia/nemotron-mini-4b-instruct", "NVIDIA: Nemotron Mini 4B"),
    ("stepfun-ai/step-3.7-flash", "StepFun: Step 3.7 Flash"),
    ("stepfun-ai/step-3.5-flash", "StepFun: Step 3.5 Flash"),
    ("upstage/solar-10.7b-instruct", "Upstage: Solar 10.7B"),
    ("abacusai/dracarys-llama-3.1-70b-instruct", "Abacus: Dracarys Llama 3.1 70B"),
]
