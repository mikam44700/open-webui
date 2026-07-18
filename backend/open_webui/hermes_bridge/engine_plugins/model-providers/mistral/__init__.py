"""Mistral AI — profil provider (plugin maison LunarIA, restauration V1).

Endpoint « La Plateforme » compatible OpenAI. Modèles curés par puissance
(cf. _CURATED_MODELS["mistral"] côté bridge) : Large > Medium > Small.
"""

from providers import register_provider
from providers.base import ProviderProfile


mistral = ProviderProfile(
    name="mistral",
    aliases=("mistralai",),
    display_name="Mistral AI",
    description="Mistral AI — modèles français, API La Plateforme (compatible OpenAI)",
    signup_url="https://console.mistral.ai/api-keys",
    env_vars=("MISTRAL_API_KEY",),
    base_url="https://api.mistral.ai/v1",
    auth_type="api_key",
    supports_vision=True,
    default_aux_model="mistral-small-latest",
    fallback_models=(
        "mistral-large-latest",
        "magistral-medium-latest",
        "mistral-small-latest",
    ),
)

register_provider(mistral)
