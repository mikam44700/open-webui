"""Together AI — profil provider (plugin maison LunarIA, restauration V1).

Hébergeur multi-modèles open-source, API compatible OpenAI. Nécessite des crédits
payants pour obtenir une clé (constat V1, 2026-07-08). Le repli ci-dessous est une
sélection tool-capable ; le catalogue live (GET /models) prime une fois connecté.
"""

from providers import register_provider
from providers.base import ProviderProfile


together = ProviderProfile(
    name="together",
    aliases=("together-ai", "togetherai"),
    display_name="Together AI",
    description="Together AI — grands modèles open-source hébergés (compatible OpenAI)",
    signup_url="https://api.together.ai/",
    env_vars=("TOGETHER_API_KEY",),
    base_url="https://api.together.xyz/v1",
    auth_type="api_key",
    fallback_models=(
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "deepseek-ai/DeepSeek-V3",
    ),
)

register_provider(together)
