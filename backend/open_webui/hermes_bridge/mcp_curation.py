"""Curation du catalogue MCP orientée client (feature « registre des 55 »).

Source de vérité UNIQUE du tri visible/expert et du rangement par catégorie.
Le registre distant (mcp_registry) fournit les MCP bruts ; ici on décide, par ``id`` :
- dans quelle **catégorie** chaque MCP apparaît (Productivité, Finance, …) ;
- s'il est **visible** par défaut (dirigeant non-tech) ou réservé au **mode expert**.

Décidé avec le client (cf. mémoire ``curation-mcp-19-visibles``) : 19 MCP visibles,
le reste en mode expert. Tout MCP inconnu de la map retombe en ``other`` / ``expert``
(jamais affiché au dirigeant par défaut, mais jamais perdu non plus).
"""

from __future__ import annotations

# Visibilité d'une entrée du catalogue.
VISIBLE = "visible"
EXPERT = "expert"

# Catégories, dans l'ordre d'affichage. ``expert_only`` = la section entière n'apparaît
# qu'en mode avancé (DevOps, Bases de données, Crypto…). Les catégories visibles peuvent
# tout de même contenir des entrées ``expert`` (ex. Finance : Stripe visible, Alpaca expert).
CATEGORY_ORDER: list[str] = [
    "productivity",
    "finance",
    "creation",
    "search",
    "devops",
    "database",
    "crypto",
    "tools",
    "other",
]

EXPERT_ONLY_CATEGORIES: set[str] = {"devops", "database", "crypto", "tools", "other"}

# id MCP -> (catégorie, visibilité). Les ``id`` suivent ceux du registre (fathah/hermes-registry)
# + ceux du catalogue moteur (n8n, unreal-engine) + le preset maison (hubspot).
CURATION: dict[str, tuple[str, str]] = {
    # --- Productivité & Bureau (10 visibles) ---
    "gmail": ("productivity", VISIBLE),
    "google-calendar": ("productivity", VISIBLE),
    "google-drive": ("productivity", VISIBLE),
    "notion": ("productivity", VISIBLE),
    "slack": ("productivity", VISIBLE),
    "asana": ("productivity", VISIBLE),
    "linear": ("productivity", VISIBLE),
    "atlassian": ("productivity", VISIBLE),
    "airtable": ("productivity", VISIBLE),
    "youtube": ("productivity", VISIBLE),
    "hubspot": ("productivity", VISIBLE),  # preset maison (hors registre)
    # --- Finance (4 visibles + 4 experts) ---
    "stripe": ("finance", VISIBLE),
    "paypal": ("finance", VISIBLE),
    "quickbooks": ("finance", VISIBLE),
    "plaid": ("finance", VISIBLE),
    "alpaca": ("finance", EXPERT),
    "polygon-io": ("finance", EXPERT),
    "dune": ("finance", EXPERT),
    "tradingview": ("finance", EXPERT),
    # --- Création & Média (4 visibles + 4 experts) ---
    "canva": ("creation", VISIBLE),
    "figma": ("creation", VISIBLE),
    "elevenlabs": ("creation", VISIBLE),
    "higgsfield": ("creation", VISIBLE),
    "meigen-ai-design": ("creation", EXPERT),
    "blender": ("creation", EXPERT),
    "ableton": ("creation", EXPERT),
    "davinci-resolve": ("creation", EXPERT),
    # --- Recherche (1 visible) ---
    "brave-search": ("search", VISIBLE),
    # --- DevOps & Développement (expert) ---
    "github": ("devops", EXPERT),
    "git": ("devops", EXPERT),
    "docker-hub": ("devops", EXPERT),
    "kubernetes": ("devops", EXPERT),
    "cloudflare": ("devops", EXPERT),
    "vercel": ("devops", EXPERT),
    "sentry": ("devops", EXPERT),
    "context7": ("devops", EXPERT),
    "playwright": ("devops", EXPERT),
    "puppeteer": ("devops", EXPERT),
    "n8n": ("devops", EXPERT),  # catalogue moteur (hors registre)
    # --- Bases de données (expert) ---
    "postgres": ("database", EXPERT),
    "supabase": ("database", EXPERT),
    "neon": ("database", EXPERT),
    "redis": ("database", EXPERT),
    "sqlite": ("database", EXPERT),
    # --- Crypto & Blockchain (expert) ---
    "base": ("crypto", EXPERT),
    "ccxt": ("crypto", EXPERT),
    "coingecko": ("crypto", EXPERT),
    "etherscan": ("crypto", EXPERT),
    "solana-agent-kit": ("crypto", EXPERT),
    "the-graph": ("crypto", EXPERT),
    "thirdweb": ("crypto", EXPERT),
    # --- Outils techniques (expert) ---
    "fetch": ("tools", EXPERT),
    "memory": ("tools", EXPERT),
    "sequential-thinking": ("tools", EXPERT),
    "filesystem": ("tools", EXPERT),
    "aws": ("tools", EXPERT),
    "mistral": ("tools", EXPERT),  # à terme : onglet « Modèles IA » (cf. mémoire)
    # --- Autres (expert) ---
    "unreal-engine": ("other", EXPERT),  # catalogue moteur (hors registre)
}

# Repli pour tout id absent de la map : rangé dans « Autres », masqué par défaut.
DEFAULT_CLASSIFICATION: tuple[str, str] = ("other", EXPERT)


def classify(entry_id: str) -> tuple[str, str]:
    """Renvoie ``(category, visibility)`` pour un id de MCP. Repli sûr si inconnu."""
    return CURATION.get((entry_id or "").strip().lower(), DEFAULT_CLASSIFICATION)
