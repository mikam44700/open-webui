"""Outils (toolsets Hermes) cochés par défaut à l'installation d'un client.

Source de vérité **produit** (humaine) : ``app/bridge/deploy/default-toolsets.md``.
Ce module en est la traduction **machine** — garder les deux synchronisés.

Principe (cohérent avec l'honnêteté des libellés) :
- ✅ coché d'office = marche **sans connexion supplémentaire**, ou capacité **cœur** de l'agent.
- ❌ décoché d'office = besoin d'une **clé / compte / modèle compatible AVANT** de servir,
  ou spécifique à une plateforme. On ne coche jamais un outil non fonctionnel.

Les deux listes couvrent l'INTÉGRALITÉ des ``CONFIGURABLE_TOOLSETS`` de Hermes (26 clés).
``DEFAULT_ENABLED_TOOLSETS`` est donc une **liste blanche complète** : tout ce qui n'y est
pas est décoché. Important : ``image_gen``, ``yuanbao`` et ``computer_use`` ne sont PAS dans
les défauts-off natifs de Hermes → sans écriture explicite de ``platform_toolsets`` ils
seraient actifs. On applique donc toujours la liste blanche pour obtenir l'état voulu.
"""

from __future__ import annotations

# ✅ Cochés d'office (15) — fonctionnent sans rien brancher, ou capacité cœur de l'agent.
DEFAULT_ENABLED_TOOLSETS: tuple[str, ...] = (
    "terminal",         # les mains de l'agent (cœur)
    "file",             # lire / écrire des fichiers (cœur)
    "code_execution",   # exécuter du code (cœur)
    "web",              # recherche web — marche sans clé (DuckDuckGo)
    "browser",          # navigateur automatisé — backend local
    "vision",           # analyse d'image — via le modèle principal (multimodal)
    "tts",              # synthèse vocale — Edge TTS gratuit
    "skills",           # compétences de l'agent — interne
    "todo",             # planification de tâches — interne
    "clarify",          # questions de clarification — interne
    "delegation",       # délégation à des sous-agents — interne
    "memory",           # mémoire persistante — interne
    "context_engine",   # moteur de contexte — interne
    "session_search",   # recherche dans les sessions — interne
    "cronjob",          # tâches planifiées — interne
)

# ❌ Décochés d'office (11) — connexion / modèle compatible requis, ou hors plateforme.
DEFAULT_DISABLED_TOOLSETS: tuple[str, ...] = (
    "x_search",         # nécessite la connexion xAI (OAuth/clé)
    "image_gen",        # nécessite un fournisseur de génération d'images
    "video_gen",        # nécessite un fournisseur de génération de vidéos
    "video",            # analyse vidéo — nécessite un modèle compatible
    "moa",              # nécessite une clé OpenRouter
    "homeassistant",    # nécessite jeton + URL Home Assistant
    "spotify",          # nécessite l'autorisation OAuth du compte
    "discord",          # nécessite un token de bot Discord
    "discord_admin",    # nécessite un token + droits admin Discord
    "yuanbao",          # nécessite une connexion Yuanbao (niche)
    "computer_use",     # macOS/desktop uniquement → inutile sur un VPS Linux
)
