"""Adapter Mixture of Agents (MoA) — configuration + activation, ZÉRO modif moteur.

MoA est une capacité NATIVE du moteur Hermes (provider virtuel « moa ») : plusieurs
« modèles de référence » (proposeurs) répondent, puis un « agrégateur » (chef de synthèse)
combine le tout. On ne touche pas au moteur : on lit/écrit son bloc de config ``moa`` via
SES propres fonctions (``hermes_cli.config.load_config/save_config`` +
``hermes_cli.moa_config.normalize_moa_config``), exécutées dans l'interpréteur de Hermes.

Activation : on met simplement le cerveau actif sur ``provider=moa`` / ``model=default``
(même mécanisme que le sélecteur de cerveau). Le moteur exécute alors sa boucle MoA tout
seul dans le chat, sans commande à taper.
"""

from __future__ import annotations

import json
import logging

from . import hermes_adapter as h
from .models import ProviderState

logger = logging.getLogger(__name__)

# Nom du preset unique géré par l'UI (le moteur en supporte plusieurs ; on en expose un).
PRESET_NAME = "default"

# Mémoire du cerveau utilisé AVANT d'activer MoA, pour y revenir à l'extinction.
# Fichier côté bridge (ne touche pas au schéma de config du moteur).
_PREV_FILE = h.HERMES_HOME / ".agentos_moa_prev.json"


def _clean_slot(slot: object) -> dict[str, str] | None:
    """Valide un slot {provider, model} ; rejette « moa » (pas de récursion)."""
    if not isinstance(slot, dict):
        return None
    provider = str(slot.get("provider") or "").strip()
    model = str(slot.get("model") or "").strip()
    if not provider or not model or provider.lower() == "moa":
        return None
    return {"provider": provider, "model": model}


def get_config() -> dict:
    """Config MoA courante : proposeurs + agrégateur + actif ?

    Lit le preset actif via les fonctions natives du moteur (repli propre si absent).
    """
    script = """
import json
import hermes_cli.config as c
import hermes_cli.moa_config as mc
cfg = c.load_config()
moa = mc.normalize_moa_config(cfg.get("moa") if isinstance(cfg, dict) else {})
print(json.dumps({
    "reference_models": moa.get("reference_models", []),
    "aggregator": moa.get("aggregator", {}),
    "enabled": bool(moa.get("enabled", False)),
}))
"""
    data = h.introspect(script)
    active = h.get_active()
    data["active"] = bool(active and active.provider_id == "moa")
    return data


def set_config(reference_models: list, aggregator: object) -> dict:
    """Écrit le preset MoA (proposeurs + agrégateur) dans ``config.yaml``.

    Garde-fous : au moins 2 proposeurs valides, un agrégateur valide, aucun « moa »
    (récursion interdite). Lève ``ValueError`` avec un message clair sinon.
    """
    refs = [s for s in (_clean_slot(x) for x in (reference_models or [])) if s]
    agg = _clean_slot(aggregator)
    if len(refs) < 2:
        raise ValueError("Choisis au moins 2 cerveaux à combiner.")
    if agg is None:
        raise ValueError("Choisis un chef de synthèse (agrégateur) valide.")

    payload = {"reference_models": refs, "aggregator": agg, "enabled": True}
    # On embarque le payload comme littéral JSON sûr dans le script moteur.
    # FUSION (pas d'écrasement, finding MOYENNE #3) : on ne remplace QUE le preset "default"
    # géré par l'UI, en conservant tel quel tout autre preset (ex. créé via le CLI Hermes en
    # direct) ainsi que toute autre clé inconnue du bloc "moa" existant — ``cfg`` est déjà
    # chargé en entier dans ce même script, pas besoin d'un aller-retour supplémentaire.
    script = f"""
import json
import hermes_cli.config as c
import hermes_cli.moa_config as mc
data = json.loads({json.dumps(json.dumps(payload))})
cfg = c.load_config()
if not isinstance(cfg, dict):
    cfg = {{}}
existing_moa = cfg.get("moa") if isinstance(cfg.get("moa"), dict) else {{}}
presets = dict(existing_moa.get("presets") or {{}})
presets[{json.dumps(PRESET_NAME)}] = data
cfg["moa"] = mc.normalize_moa_config({{
    **existing_moa,
    "presets": presets,
    "default_preset": {json.dumps(PRESET_NAME)},
}})
c.save_config(cfg)
print(json.dumps({{"ok": True}}))
"""
    h.introspect(script)
    return get_config()


def activate() -> dict:
    """Fait de MoA le cerveau actif (le chat l'utilise alors automatiquement).

    Mémorise le cerveau courant (s'il n'est pas déjà MoA) pour pouvoir y revenir à
    l'extinction.
    """
    cur = h.get_active()
    if cur and cur.provider_id != "moa":
        try:
            _PREV_FILE.write_text(json.dumps({"provider": cur.provider_id, "model": cur.model_id}))
        except OSError:
            logger.debug(
                "mémorisation du cerveau précédent (%s) avant activation de MoA échouée (non bloquant)",
                cur.provider_id,
                exc_info=True,
            )
    h.set_active("moa", PRESET_NAME)
    return get_config()


def deactivate() -> dict:
    """Éteint MoA : revient au cerveau utilisé juste avant (ou, à défaut, au 1er connecté).

    Repasse par ``h.activate_provider`` — le MÊME chemin sûr que le sélecteur de cerveau
    normal (``routers/providers.py``), au lieu d'appeler ``h.set_active`` bas niveau
    directement (cf. audit phase 3, finding HAUTE) : un provider mémorisé qui serait
    devenu déconnecté entre-temps (clé révoquée, OAuth expiré...) ne peut donc plus jamais
    redevenir silencieusement le cerveau actif — on retombe alors sur le repli (1er cerveau
    connecté), sans jamais planter le chat avec un cerveau fantôme.
    """
    prev = None
    try:
        if _PREV_FILE.exists():
            prev = json.loads(_PREV_FILE.read_text())
    except (OSError, ValueError):
        prev = None

    if prev and prev.get("provider") and prev["provider"] != "moa":
        try:
            h.activate_provider(prev["provider"], prev.get("model") or "default")
            return get_config()
        except (h.UnknownProvider, h.ProviderNotConfigured) as exc:
            # le provider mémorisé n'existe plus / n'est plus connecté -> repli ci-dessous
            logger.debug(
                "provider mémorisé %r indisponible à la désactivation de MoA (%s) — repli sur le 1er connecté",
                prev.get("provider"),
                exc,
            )

    # Repli : 1er cerveau connecté (non-moa) avec au moins un modèle.
    fallback = next(
        (
            p
            for p in h.list_providers()
            if p.state != ProviderState.not_configured and p.id != "moa" and p.models
        ),
        None,
    )
    if fallback is None:
        raise ValueError("Aucun autre cerveau connecté vers lequel revenir.")
    h.activate_provider(fallback.id, fallback.models[0].id)
    return get_config()
