"""Baidu ERNIE — profil provider (plugin maison LunarIA, restauration V1).

Grands modèles ERNIE de Baidu via la plateforme Qianfan (endpoint v2 compatible
OpenAI). Classé dans l'onglet « Autres » côté bridge (_OTHER_SLUGS : cloud
entreprise chinois, région/endpoint à la Bedrock/Azure).
"""

from providers import register_provider
from providers.base import ProviderProfile


baidu_ernie = ProviderProfile(
    name="baidu-ernie",
    aliases=("baidu", "ernie", "qianfan"),
    display_name="Baidu ERNIE",
    description="Baidu ERNIE — modèles ERNIE 4.5 / X1 via Qianfan (compatible OpenAI)",
    signup_url="https://console.bce.baidu.com/iam/#/iam/apikey",
    env_vars=("BAIDU_API_KEY", "QIANFAN_API_KEY"),
    base_url="https://qianfan.baidubce.com/v2",
    auth_type="api_key",
    fallback_models=(
        "ernie-4.5-turbo-128k",
        "ernie-x1-turbo-32k",
    ),
)

register_provider(baidu_ernie)
