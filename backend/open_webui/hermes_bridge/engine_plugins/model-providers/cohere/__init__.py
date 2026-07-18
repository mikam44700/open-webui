"""Cohere — profil provider (plugin maison LunarIA, restauration V1).

Endpoint « compatibility » officiel de Cohere (format OpenAI). Modèles curés :
cf. _COHERE_CURATED_MODELS côté bridge (7 modèles Command validés).
"""

from providers import register_provider
from providers.base import ProviderProfile


cohere = ProviderProfile(
    name="cohere",
    display_name="Cohere",
    description="Cohere — spécialiste entreprise et documents (endpoint compatible OpenAI)",
    signup_url="https://dashboard.cohere.com/api-keys",
    env_vars=("COHERE_API_KEY",),
    base_url="https://api.cohere.ai/compatibility/v1",
    auth_type="api_key",
    fallback_models=(
        "command-a-plus-05-2026",
        "command-a-reasoning-08-2025",
        "command-a-vision-07-2025",
        "command-a-03-2025",
    ),
)

register_provider(cohere)
