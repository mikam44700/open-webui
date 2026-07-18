"""Briefing Agent OS (feature 015) — assemble le « briefing du jour » de façon déterministe.

Le bridge agrège ce qu'il sait déjà : l'**agenda du jour** (calendar_adapter / Google),
les **tâches en cours** (kanban_adapter) et les **automatisations actives** (automations_adapter).
Pas de LLM : un résumé fiable et vérifiable, aligné sur le « briefing matinal » de la VISION.

Chaque source est isolée : si l'une est indisponible, sa section est marquée honnêtement
(« indisponible »), le reste du briefing s'affiche quand même.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import automations_adapter, calendar_adapter, kanban_adapter
from .hermes_adapter import HermesUnavailable

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# Fuseau du dirigeant, PAS celui du process bridge (fix audit phase 3, finding HAUTE) :
# aucun profil/config ne porte aujourd'hui le fuseau du client (recherché dans profiles_adapter,
# schemas.py, memory_adapter, deploy/*.sh — rien trouvé), donc pas de valeur par défaut
# meilleure que celle-ci tant que ce réglage n'existe pas ailleurs dans le produit. Défaut
# choisi et documenté : "Europe/Paris" (marché cible du produit, cf. CLAUDE.md), configurable
# par variable d'env pour un futur client hors de ce fuseau (même convention "AGENTOS_" que
# le reste du bridge, ex. AGENTOS_COMPOSE_FILE).
_DEFAULT_COMPANY_TZ = "Europe/Paris"


def _company_timezone() -> ZoneInfo:
    """Fuseau IANA du dirigeant. ``AGENTOS_COMPANY_TZ`` si posé, sinon ``_DEFAULT_COMPANY_TZ``.

    Un nom de fuseau invalide retombe honnêtement sur le défaut plutôt que de faire planter
    tout le briefing (dégradation cohérente avec le reste du module : chaque source isolée).
    """
    name = os.environ.get("AGENTOS_COMPANY_TZ", "").strip() or _DEFAULT_COMPANY_TZ
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(_DEFAULT_COMPANY_TZ)


def _date_label(d: datetime) -> str:
    return f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]} {d.year}"


def _events_today(tz: ZoneInfo) -> tuple[str, list[dict]]:
    """(statut, événements du jour). Statut : 'ok' | 'not_connected' | 'unavailable'.

    La fenêtre « aujourd'hui » est calculée dans le fuseau DU DIRIGEANT (``tz``), pas celui
    du process bridge — sinon, sur un VPS en UTC, un rendez-vous proche de minuit heure
    locale tombe dans le mauvais jour (cf. audit phase 3, finding HAUTE). Le même ``tz`` est
    transmis à ``calendar_adapter.list_events`` pour aligner Outlook/Calendly (Google ignore
    ce paramètre, déjà correct par construction).
    """
    try:
        if not calendar_adapter.calendar_status().get("connected"):
            return "not_connected", []
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        events = calendar_adapter.list_events(start.isoformat(), end.isoformat(), tz=str(tz))
        return "ok", events
    except calendar_adapter.GoogleNotConnected:
        return "not_connected", []
    except Exception:
        return "unavailable", []


def _tasks_open() -> tuple[str, list[dict]]:
    try:
        resp = kanban_adapter.list_tasks()
        tasks = [t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in resp.tasks]
        open_tasks = [t for t in tasks if (t.get("status") or "").lower() != "done"]
        return "ok", open_tasks[:8]
    except HermesUnavailable:
        return "unavailable", []
    except Exception:
        return "unavailable", []


def _automations_active() -> tuple[str, list[dict]]:
    try:
        autos = automations_adapter.list_automations()
        return "ok", [a for a in autos if a.get("status") == "active"]
    except HermesUnavailable:
        return "unavailable", []
    except Exception:
        return "unavailable", []


def build_briefing() -> dict:
    """Assemble le briefing structuré + un texte prêt à publier dans un canal.

    « Aujourd'hui » (libellé de date + fenêtre agenda) est calculé dans le fuseau du
    dirigeant (``_company_timezone``), jamais celui — arbitraire — du process bridge.
    """
    tz = _company_timezone()
    now = datetime.now(tz)
    ev_status, events = _events_today(tz)
    tasks_status, tasks = _tasks_open()
    auto_status, automations = _automations_active()

    briefing = {
        "date_label": _date_label(now),
        "events_status": ev_status,
        "events": events,
        "tasks_status": tasks_status,
        "tasks": tasks,
        "automations_status": auto_status,
        "automations": automations,
    }
    briefing["text"] = _render_text(briefing)
    return briefing


def _render_text(b: dict) -> str:
    """Version texte (Markdown léger) pour publication dans le canal Agent OS."""
    lines = [f"**Briefing du {b['date_label']}**", ""]

    # Agenda
    if b["events_status"] == "ok":
        if b["events"]:
            lines.append(f"🗓️ **Agenda du jour** ({len(b['events'])})")
            for e in b["events"][:6]:
                loc = f" — {e['location']}" if e.get("location") else ""
                lines.append(f"• {e.get('when_label', '')} : {e.get('title', '')}{loc}")
        else:
            lines.append("🗓️ **Agenda du jour** : rien de prévu.")
    elif b["events_status"] == "not_connected":
        lines.append("🗓️ Agenda : connectez Google dans Intégrations pour voir vos rendez-vous.")
    else:
        lines.append("🗓️ Agenda : momentanément indisponible.")
    lines.append("")

    # Tâches
    if b["tasks_status"] == "ok":
        if b["tasks"]:
            lines.append(f"✅ **Tâches en cours** ({len(b['tasks'])})")
            for t in b["tasks"][:6]:
                lines.append(f"• {t.get('title', '(sans titre)')}")
        else:
            lines.append("✅ **Tâches** : aucune tâche en cours.")
    else:
        lines.append("✅ Tâches : momentanément indisponibles.")
    lines.append("")

    # Automatisations
    if b["automations_status"] == "ok":
        n = len(b["automations"])
        if n:
            lines.append(f"⚡ **Automatisations actives** : {n}")
        else:
            lines.append("⚡ **Automatisations** : aucune active.")
    else:
        lines.append("⚡ Automatisations : momentanément indisponibles.")

    return "\n".join(lines)
