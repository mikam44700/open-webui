"""Z.AI / GLM — liste curée + détection du mode (clé API classique vs Coding Plan)

La carte Z.AI (``zai``) couvre DEUX modes selon la clé collée, que le moteur route vers
deux endpoints distincts (auto-détection interne, cf. ``detect_zai_endpoint``) :
  - clé API CLASSIQUE → https://api.z.ai/api/paas/v4        (paiement à l'usage)
  - clé CODING PLAN   → https://api.z.ai/api/coding/paas/v4 (forfait mensuel)
Le profil moteur expose une liste FIGÉE unique (glm-5.2…glm-4.5-flash), la MÊME quel que
soit le mode et non triée par accessibilité. Test réel (2026-07-07, clé classique SANS crédit) :
  - glm-5.x / glm-4.x → HTTP 429 « Insufficient balance » (payants à l'usage) ;
  - SEULS répondent sans crédit : glm-4.7-flash, glm-4.5-flash (200) → « gratuits » ;
  - glm-4.6v-flash → 429 (pas réellement gratuit) → écarté des gratuits.
On cure donc : GRATUITS en tête, PAYANTS marqués « 💳 crédit requis ». Le garde-fou
d'auto-activation (_RECOMMENDED_MODEL["zai"] = glm-4.7-flash) évite d'activer un modèle payant
(429 au 1er message) pour un client sans crédit ; en mode Coding Plan (glm-4.7-flash absent de
la liste) le repli ``_default_model_for`` tombe sur le 1er du forfait (glm-5.2, inclus).

Détection du MODE (fiable pour ce qui compte) : une clé Coding Plan a un forfait actif →
glm-5.2 répond 200 sur l'endpoint CODING. Une clé classique n'y parvient jamais (429 sans
crédit, ou elle paie sur l'endpoint classique). Donc « 200 sur coding » ⟺ Coding Plan. On sonde
aussi l'endpoint classique pour distinguer classique-payé (glm-5.2 → 200 : on retire « crédit
requis ») de classique-gratuit (429). Résultat caché PAR CLÉ (TTL 30 min), comme Ollama.
Limite assumée : une clé classique AVEC crédit qui serait facturée sur l'endpoint coding
apparaîtrait « Coding Plan » (edge rare, bénin — le sous-ensemble affiché reste valide).
Zéro modif moteur.
"""

from __future__ import annotations

import json
import time

_ZAI_BASE_CLASSIC = "https://api.z.ai/api/paas/v4"
_ZAI_BASE_CODING = "https://api.z.ai/api/coding/paas/v4"
# Miroir de « (gratuit) » : le contraste gratuit / payant est le plus clair pour un dirigeant
# non-tech. On dit « payant » (pay-as-you-go, à l'usage) et JAMAIS « abonnement » — l'abonnement
# c'est le Coding Plan (autre mode) ; l'écrire sur l'API classique tromperait le client. Retiré
# dynamiquement si la clé a du crédit (mode classic_paid) ou en Coding Plan (tout inclus).
_ZAI_CREDIT_TAG = " (payant)"

# Gratuits (répondent sans crédit sur l'endpoint classique — test réel).
_ZAI_FREE_MODELS: list[tuple[str, str]] = [
    ("glm-4.7-flash", "GLM : GLM-4.7 Flash (gratuit)"),
    ("glm-4.5-flash", "GLM : GLM-4.5 Flash (gratuit)"),
]
# Payants à l'usage (classique) : 429 sans crédit. Tag « (payant) » retiré si la clé paie.
# Récent → ancien. Vérifié via /models (les 8 GLM) + test réel (existent = 429 sans crédit).
_ZAI_PAID_MODELS: list[tuple[str, str]] = [
    ("glm-5.2", "GLM : GLM-5.2" + _ZAI_CREDIT_TAG),
    ("glm-5.1", "GLM : GLM-5.1" + _ZAI_CREDIT_TAG),
    ("glm-5", "GLM : GLM-5" + _ZAI_CREDIT_TAG),
    ("glm-5v-turbo", "GLM : GLM-5V Turbo (vision)" + _ZAI_CREDIT_TAG),
    ("glm-5-turbo", "GLM : GLM-5 Turbo" + _ZAI_CREDIT_TAG),
    ("glm-4.7", "GLM : GLM-4.7" + _ZAI_CREDIT_TAG),
    ("glm-4.6", "GLM : GLM-4.6" + _ZAI_CREDIT_TAG),
    ("glm-4.5", "GLM : GLM-4.5" + _ZAI_CREDIT_TAG),
    ("glm-4.5-air", "GLM : GLM-4.5-Air" + _ZAI_CREDIT_TAG),
]

_ZAI_MODE_TTL = 30 * 60  # 30 min
_zai_mode_cache: dict = {"key": None, "mode": None, "ts": 0.0}


def _zai_read_key() -> str | None:
    """Clé Z.AI présente dans ``.env`` (1re des 3 variables acceptées par le moteur)."""
    from providers_bridge import hermes_adapter as ha

    for name in ("GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY"):
        val = ha.read_env_value(name)
        if val:
            return val
    return None


def _zai_probe(base_url: str, api_key: str) -> int | None:
    """Sonde glm-5.2 sur ``base_url`` (max_tokens=1). Renvoie le code HTTP, ``None`` si réseau KO."""
    from providers_bridge import hermes_adapter as ha

    body = json.dumps({
        "model": "glm-5.2",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    })
    status, _reason, _err = ha._http_status(
        f"{base_url}/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST", body=body,
    )
    return status


def _zai_mode(api_key: str) -> str:
    """Mode de la clé Z.AI, caché par clé (TTL 30 min) :
    - ``"coding"``       : Coding Plan actif (glm-5.2 → 200 sur l'endpoint coding).
    - ``"classic_paid"`` : clé classique AVEC crédit (glm-5.2 → 200 sur l'endpoint classique).
    - ``"classic_free"`` : clé classique sans crédit / défaut (jamais de faux Coding Plan).
    Ne lève jamais. Un probe ne coûte quasi rien (max_tokens=1 ; 429 immédiat sans crédit)."""
    # Passe par le module hermes_adapter : les tests monkeypatchent ``ha._zai_probe`` et
    # remplacent ``ha._zai_mode_cache`` par un dict neuf — cette fonction (ré-exportée sous
    # le même nom) doit observer les deux. cf. providers/__init__.py.
    from providers_bridge import hermes_adapter as ha

    now = time.time()
    c = ha._zai_mode_cache
    if c["key"] == api_key and c["mode"] is not None and (now - c["ts"]) < _ZAI_MODE_TTL:
        return c["mode"]
    mode = "classic_free"
    if ha._zai_probe(_ZAI_BASE_CODING, api_key) == 200:
        mode = "coding"
    elif ha._zai_probe(_ZAI_BASE_CLASSIC, api_key) == 200:
        mode = "classic_paid"
    ha._zai_mode_cache.update({"key": api_key, "mode": mode, "ts": now})
    return mode


def _zai_model_pairs() -> list[tuple[str, str]]:
    """Modèles Z.AI pour le sélecteur, selon le mode détecté de la clé configurée :
    - Coding Plan : TOUS les GLM (le forfait sert les mêmes que l'API classique — vérifié :
      /models coding == /models classique), inclus donc sans marquage, sans les Flash gratuits.
    - Classique payé : gratuits en tête + payants SANS « (payant) » (la clé a du crédit).
    - Classique gratuit / clé absente : gratuits en tête + payants « (payant) »."""
    # cf. commentaire de _zai_mode : lookup via ha (siblings monkeypatchés dans les tests).
    from providers_bridge import hermes_adapter as ha

    api_key = ha._zai_read_key()
    mode = ha._zai_mode(api_key) if api_key else "classic_free"
    paid_no_tag = [(mid, lbl.replace(_ZAI_CREDIT_TAG, "")) for mid, lbl in _ZAI_PAID_MODELS]
    if mode == "coding":
        return paid_no_tag
    if mode == "classic_paid":
        return list(_ZAI_FREE_MODELS) + paid_no_tag
    return list(_ZAI_FREE_MODELS) + list(_ZAI_PAID_MODELS)
