"""Perplexity Sonar — profil provider (plugin maison LunarIA, restauration V1).

ATTENTION (décision V1, 2026-07-06) : aucun modèle Sonar ne supporte le tool
calling → incompatible avec le chat agentique Hermes. Le provider est donc MASQUÉ
dans l'interface (HIDDEN_PROVIDER_IDS côté front) mais le plugin est conservé pour
parité V1, réversible si Perplexity ouvre le tool calling un jour.

Pas d'endpoint GET /models chez Perplexity → health check désactivé.
"""

from providers import register_provider
from providers.base import ProviderProfile


perplexity = ProviderProfile(
    name="perplexity",
    aliases=("perplexity-sonar", "sonar"),
    display_name="Perplexity Sonar",
    description="Perplexity Sonar — answer engine (sans tool calling, masqué en interface)",
    signup_url="https://www.perplexity.ai/settings/api",
    env_vars=("PERPLEXITY_API_KEY",),
    base_url="https://api.perplexity.ai",
    auth_type="api_key",
    supports_health_check=False,
    fallback_models=(
        "sonar-pro",
        "sonar-reasoning-pro",
        "sonar",
    ),
)

register_provider(perplexity)
