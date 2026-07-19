"""Adapter Garde-fous (chantier Guardrails, SPEC-guardrails.md) — ZÉRO modif moteur.

Le MOAT « Boucle de confiance » côté serveur : c'est le bridge qui tient les portes,
jamais l'agent (principe governed-agents, recherche du 2026-07-19). Trois protections
NATIVES du moteur Hermes, qu'on arme et qu'on expose à l'app :

- **Disjoncteur de boucle** (``tool_loop_guardrails``) : avertissements + hard stops
  quand un outil échoue en boucle ou ne progresse plus. On active les hard stops.
- **Approbation mémoire** (``memory.write_approval``) : rien ne s'écrit dans la mémoire
  sans validation — les écritures restent en attente (file jugée par le patron dans l'app).
- **File d'attente mémoire** : liste / approuve / rejette les écritures en attente, en
  réutilisant les fonctions du moteur lui-même (même recette que le gateway ``/memory``).

Tout passe par ``hermes_adapter.introspect`` (l'interpréteur de Hermes, HERMES_HOME
du bridge) : on ne réimplémente aucun format du moteur.
"""

from __future__ import annotations

import json
import logging

import yaml

from . import hermes_adapter as h

logger = logging.getLogger(__name__)

# Seuils du disjoncteur qu'on ARME (défauts du moteur, hard stop activé en plus).
# Alignés sur cli-config.yaml.example du moteur — on n'invente aucun réglage.
ARMED_GUARDRAILS = {
    "warnings_enabled": True,
    "hard_stop_enabled": True,
}


# ---------------------------------------------------------------------------
# État
# ---------------------------------------------------------------------------

def get_state() -> dict:
    """État des protections, lu dans config.yaml (source de vérité du moteur)."""
    cfg_path = h.HERMES_HOME / "config.yaml"
    cfg: dict = {}
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
    guardrails = cfg.get("tool_loop_guardrails") or {}
    memory = cfg.get("memory") or {}
    return {
        "loop_breaker": {
            "warnings_enabled": bool(guardrails.get("warnings_enabled", True)),
            "hard_stop_enabled": bool(guardrails.get("hard_stop_enabled", False)),
            "warn_after": guardrails.get("warn_after") or {},
            "hard_stop_after": guardrails.get("hard_stop_after") or {},
        },
        "memory_write_approval": bool(memory.get("write_approval", False)),
        "pending_memory": pending_memory_count(),
    }


# ---------------------------------------------------------------------------
# Armement (idempotent — rejoué à chaque démarrage du backend)
# ---------------------------------------------------------------------------

_ARM_SCRIPT = """
import json
from hermes_cli import config as c

cfg = c.load_config()
changed = False

guardrails = cfg.setdefault("tool_loop_guardrails", {})
for key, value in (("warnings_enabled", True), ("hard_stop_enabled", True)):
    if guardrails.get(key) is not value:
        guardrails[key] = value
        changed = True

memory = cfg.setdefault("memory", {})
if memory.get("write_approval") is not True:
    memory["write_approval"] = True
    changed = True

if changed:
    c.save_config(cfg)
print(json.dumps({"changed": changed}))
"""


def arm() -> dict:
    """Arme les protections dans config.yaml via les propres fonctions du moteur.

    Idempotent : ne réécrit le fichier que si un réglage manquait. Le moteur relit
    config.yaml à chaud (même mécanisme que le sélecteur de cerveau) — les nouvelles
    sessions de chat appliquent le réglage sans redémarrage du gateway.
    """
    result = h.introspect(_ARM_SCRIPT)
    if result.get("changed"):
        logger.info("guardrails: protections armées dans config.yaml (hard stop + approbation mémoire)")
    return get_state()


def arm_on_startup() -> None:
    """Armement au démarrage du backend, best-effort (jamais bloquant, jamais fatal).

    Même philosophie que la réinstallation des plugins moteur : ce qui doit survivre
    aux redémarrages et aux volumes neufs est rejoué à chaque boot, idempotent.
    """
    try:
        arm()
    except Exception as exc:  # moteur absent (dev sans Hermes) : l'app démarre quand même
        logger.warning("guardrails: armement au démarrage impossible (%s)", exc)


# ---------------------------------------------------------------------------
# File d'approbation mémoire (même recette que le gateway /memory)
# ---------------------------------------------------------------------------

_LIST_SCRIPT = """
import json
from tools import write_approval as wa
print(json.dumps(wa.list_pending(wa.MEMORY)))
"""


def list_pending_memory() -> list[dict]:
    """Écritures mémoire en attente d'approbation (id, summary, origin...)."""
    return h.introspect(_LIST_SCRIPT)


def pending_memory_count() -> int:
    try:
        return len(list_pending_memory())
    except h.HermesUnavailable:
        return 0


# Application d'une écriture approuvée : miroir exact du gateway (_handle_memory_command) —
# store frais chargé du disque, apply_memory_pending du moteur, puis retrait de la file.
_DECIDE_SCRIPT = """
import json, sys
from tools import write_approval as wa

target = {target!r}
decision = {decision!r}

records = wa.list_pending(wa.MEMORY)
if target != "all":
    rec = wa.get_pending(wa.MEMORY, target)
    records = [rec] if rec else []

applied, failed = 0, []
if decision == "approve":
    from tools.memory_tool import apply_memory_pending, load_on_disk_store
    store = load_on_disk_store()
    for rec in records:
        try:
            result = apply_memory_pending(rec.get("payload", {{}}), store)
            ok, err = bool(result.get("success")), result.get("error", "")
        except Exception as exc:
            ok, err = False, str(exc)
        if ok:
            wa.discard_pending(wa.MEMORY, rec["id"])
            applied += 1
        else:
            failed.append({{"id": rec["id"], "error": err}})
else:
    for rec in records:
        if wa.discard_pending(wa.MEMORY, rec["id"]):
            applied += 1

print(json.dumps({{"decision": decision, "count": applied, "failed": failed,
                   "not_found": target != "all" and not records}}))
"""


def decide_memory(pending_id: str, decision: str) -> dict:
    """Approuve (``approve``) ou rejette (``reject``) une écriture en attente.

    ``pending_id`` peut être ``all``. Approuver = appliquer réellement l'écriture au
    store mémoire du moteur PUIS la retirer de la file ; rejeter = retirer sans écrire.
    """
    if decision not in ("approve", "reject"):
        raise ValueError(f"décision inconnue: {decision}")
    script = _DECIDE_SCRIPT.format(target=pending_id, decision=decision)
    return h.introspect(script, timeout=60)
