"""Cerebras — profil provider (plugin maison LunarIA, restauration V1).

Catalogue officiel volontairement court (3 modèles, chacun optimisé pour la puce
WSE → ultra-rapide), tous tool-capable et gratuits (1M tokens/j). Testés en réel
2026-07-08, cf. providers/cerebras.py côté bridge (catalogue live).
"""

from providers import register_provider
from providers.base import ProviderProfile


cerebras = ProviderProfile(
    name="cerebras",
    display_name="Cerebras",
    description="Cerebras — inférence ultra-rapide sur puce WSE, tier gratuit",
    signup_url="https://cloud.cerebras.ai/",
    env_vars=("CEREBRAS_API_KEY",),
    base_url="https://api.cerebras.ai/v1",
    auth_type="api_key",
    fallback_models=(
        "gpt-oss-120b",
        "gemma-4-31b",
        "zai-glm-4.7",
    ),
)

register_provider(cerebras)
