"""Sakana Fugu — profil provider (plugin maison LunarIA, restauration V1).

Système multi-agents livré comme UN seul modèle : variantes « fugu » (rapide) et
« fugu-ultra » (qualité max). Affiché dans l'onglet « Modèles IA combinés » côté
front (MULTIAGENT_IDS), pas dans les Clés API.

NB : l'endpoint exact de la V1 est perdu (ancien bridge supprimé) — base_url
reconstruite depuis la fiche V1 (console.sakana.ai). Health check désactivé par
prudence ; à ajuster si la validation de clé échoue.
"""

from providers import register_provider
from providers.base import ProviderProfile


sakana = ProviderProfile(
    name="sakana",
    aliases=("sakana-ai", "fugu"),
    display_name="Sakana Fugu",
    description="Sakana Fugu — plusieurs modèles IA en un seul, prêt à l'emploi",
    signup_url="https://console.sakana.ai",
    env_vars=("SAKANA_API_KEY",),
    base_url="https://api.sakana.ai/v1",
    auth_type="api_key",
    supports_health_check=False,
    default_aux_model="fugu",
    fallback_models=(
        "fugu",
        "fugu-ultra",
    ),
)

register_provider(sakana)
