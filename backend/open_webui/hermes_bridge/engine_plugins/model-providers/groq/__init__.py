"""Groq — profil provider (plugin maison LunarIA, restauration V1).

Inférence ultra-rapide (puces LPU), tier gratuit généreux. Les 7 modèles du repli
sont tous tool-capable (testés en réel 2026-07-08, cf. providers/groq.py côté
bridge, qui rafraîchit ce catalogue en live une fois la clé posée).
"""

from providers import register_provider
from providers.base import ProviderProfile


groq = ProviderProfile(
    name="groq",
    display_name="Groq",
    description="Groq — inférence ultra-rapide (LPU), tier gratuit généreux",
    signup_url="https://console.groq.com/keys",
    env_vars=("GROQ_API_KEY",),
    base_url="https://api.groq.com/openai/v1",
    auth_type="api_key",
    default_aux_model="llama-3.1-8b-instant",
    fallback_models=(
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "qwen/qwen3-32b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-8b-instant",
    ),
)

register_provider(groq)
