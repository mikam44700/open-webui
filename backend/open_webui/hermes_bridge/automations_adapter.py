"""Adapter Automatisations — pilote le planificateur (cron) natif de Hermes.

Source de vérité = Hermes. Le bridge est sans état : il traduit l'API jobs d'Hermes
(``/api/jobs`` sur ``127.0.0.1:<port>``, Bearer ``API_SERVER_KEY``) en un modèle épuré et
francisé pour le dirigeant, et inversement (rythme simple → ``schedule`` Hermes).

Garde-fous :
- secrets jamais renvoyés au front (``origin``, identifiants de canaux, chemins) ;
- ``deliver`` et les réglages bruts ne sortent qu'en Mode Expert ;
- état toujours dérivé de la vérité Hermes (jamais supposé) ;
- Hermes injoignable → ``HermesUnavailable`` (le router répond 503, pas de repli natif).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from . import hermes_adapter
from .hermes_adapter import HermesUnavailable

_TIMEOUT = 20


class AutomationNotFound(Exception):
    """L'automatisation (job) demandée n'existe pas côté Hermes."""


class AutomationInvalid(Exception):
    """Données d'automatisation invalides (rythme/instruction) — rien n'est créé."""


# ─── Transport vers l'API jobs de Hermes ────────────────────────────────────


def _base_url() -> str:
    return f"http://127.0.0.1:{hermes_adapter._api_server_port()}"


def _request(method: str, path: str, body: dict | None = None) -> dict:
    """Appel JSON authentifié à l'API jobs de Hermes. Lève HermesUnavailable/NotFound."""
    url = f"{_base_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    key = hermes_adapter._api_server_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise AutomationNotFound() from exc
        if exc.code == 400:
            detail = _read_error(exc) or "requête invalide"
            raise AutomationInvalid(detail) from exc
        # 401/403/5xx : on considère le planificateur indisponible / mal configuré
        raise HermesUnavailable(f"API jobs Hermes: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise HermesUnavailable(str(exc)) from exc


def _read_error(exc: urllib.error.HTTPError) -> str | None:
    try:
        payload = json.loads(exc.read().decode())
        err = payload.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or "")[:200]
        return str(err or payload)[:200]
    except Exception:
        return None


# ─── Traduction rythme simple → schedule Hermes ─────────────────────────────

_WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def rhythm_to_schedule(rhythm: dict) -> str:
    """Convertit un preset dirigeant en chaîne ``schedule`` comprise par Hermes.

    daily/weekly → cron ; interval → ``every Nm`` ; once → timestamp ISO ;
    advanced → expression transmise telle quelle (Mode Expert).
    """
    kind = (rhythm or {}).get("type")
    if kind == "advanced":
        sched = str(rhythm.get("schedule") or "").strip()
        if not sched:
            raise AutomationInvalid("expression de planification vide")
        return sched
    if kind == "interval":
        minutes = rhythm.get("every_minutes")
        if not isinstance(minutes, int) or minutes < 1:
            raise AutomationInvalid("intervalle invalide")
        return f"every {minutes}m"
    if kind == "once":
        at = str(rhythm.get("at") or "").strip()
        if not at:
            raise AutomationInvalid("date/heure manquante")
        return at
    if kind in ("daily", "weekly"):
        hour, minute = _parse_hhmm(rhythm.get("time"))
        if kind == "daily":
            return f"{minute} {hour} * * *"
        weekday = rhythm.get("weekday")
        if not isinstance(weekday, int) or not 0 <= weekday <= 6:
            raise AutomationInvalid("jour de semaine invalide")
        cron_dow = (weekday + 1) % 7  # 0=lundi(UI) → 1 ; 6=dimanche(UI) → 0 (cron)
        return f"{minute} {hour} * * {cron_dow}"
    raise AutomationInvalid("type de rythme inconnu")


def _parse_hhmm(value) -> tuple[int, int]:
    try:
        h, m = str(value).split(":")
        hour, minute = int(h), int(m)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (ValueError, AttributeError):
        pass
    raise AutomationInvalid("heure invalide (attendu HH:MM)")


# ─── Traduction job Hermes → automatisation (vue dirigeant, épurée) ──────────


def _rhythm_label(schedule: dict, schedule_display: str | None) -> str:
    """Libellé français du rythme à partir du schedule structuré de Hermes."""
    kind = (schedule or {}).get("kind")
    if kind == "interval":
        minutes = schedule.get("minutes") or 0
        if minutes and minutes % 60 == 0:
            h = minutes // 60
            return "toutes les heures" if h == 1 else f"toutes les {h} heures"
        return f"toutes les {minutes} minutes"
    if kind == "once":
        run_at = schedule.get("run_at") or ""
        return f"une seule fois — {_fmt_dt(run_at)}" if run_at else "une seule fois"
    if kind == "cron":
        return _cron_label(schedule.get("expr") or schedule_display or "")
    return schedule_display or "rythme personnalisé"


def _cron_label(expr: str) -> str:
    """Reconnaît nos presets cron (M H * * * et M H * * J) pour un libellé FR lisible."""
    parts = expr.split()
    if len(parts) == 5 and parts[2] == "*" and parts[3] == "*":
        minute, hour, dow = parts[0], parts[1], parts[4]
        if minute.isdigit() and hour.isdigit():
            hhmm = f"{int(hour):02d}:{int(minute):02d}"
            if dow == "*":
                return f"tous les jours à {hhmm}"
            if dow.isdigit():
                ui = (int(dow) - 1) % 7  # cron → UI (0=lundi)
                return f"chaque {_WEEKDAYS_FR[ui]} à {hhmm}"
    return f"réglage avancé ({expr})"


def _fmt_dt(iso: str) -> str:
    """Format court FR ``JJ/MM à HH:MM`` depuis un timestamp ISO (sans dépendance externe)."""
    if not iso:
        return ""
    try:
        date_part, _, time_part = iso.partition("T")
        y, mo, d = date_part.split("-")[:3]
        hm = ":".join(time_part.replace("Z", "").split(":")[:2]) if time_part else ""
        return f"{d}/{mo} à {hm}" if hm else f"{d}/{mo}"
    except Exception:
        return iso[:16]


def _status(job: dict) -> str:
    state = job.get("state")
    if state == "completed":
        return "done"
    if state == "error" or job.get("last_status") == "error":
        return "error"
    if job.get("enabled") is False or state == "paused":
        return "paused"
    return "active"


def job_to_automation(job: dict, expert: bool = False) -> dict:
    """Projette un job Hermes en automatisation épurée. ``expert`` ajoute les champs avancés."""
    schedule = job.get("schedule") or {}
    schedule_display = job.get("schedule_display")
    next_at = job.get("next_run_at")
    last_at = job.get("last_run_at")
    last_error = job.get("last_error")
    automation = {
        "id": job.get("id"),
        "name": job.get("name") or "(sans nom)",
        "instruction": job.get("prompt") or "",
        "rhythm_label": _rhythm_label(schedule, schedule_display),
        "rhythm_kind": "once" if schedule.get("kind") == "once" else "recurrent",
        "status": _status(job),
        "next_run_label": (f"le {_fmt_dt(next_at)}" if next_at else None),
        "last_run_label": (f"le {_fmt_dt(last_at)}" if last_at else None),
        "last_status": job.get("last_status"),
        "last_error_short": (str(last_error)[:200] if last_error else None),
    }
    if expert:
        automation["schedule_raw"] = schedule_display or ""
        automation["repeat"] = job.get("repeat")
        automation["skills"] = job.get("skills") or []
        automation["deliver"] = job.get("deliver")
    return automation


# ─── Opérations (consommées par le router) ──────────────────────────────────


def list_automations(expert: bool = False) -> list[dict]:
    payload = _request("GET", "/api/jobs?include_disabled=true")
    jobs = payload.get("jobs") or []
    return [job_to_automation(j, expert) for j in jobs]


def get_automation(automation_id: str, expert: bool = False) -> dict:
    payload = _request("GET", f"/api/jobs/{automation_id}")
    return job_to_automation(payload.get("job") or {}, expert)


def create_automation(data: dict, expert: bool = False) -> dict:
    instruction = (data.get("instruction") or "").strip()
    skills = data.get("skills") or []
    if not instruction and not skills:
        raise AutomationInvalid("instruction manquante")
    body: dict = {
        "name": (data.get("name") or "").strip() or "Automatisation",
        "schedule": rhythm_to_schedule(data.get("rhythm") or {}),
        "prompt": instruction,
    }
    if skills:
        body["skills"] = skills
    if data.get("deliver"):
        body["deliver"] = data["deliver"]
    payload = _request("POST", "/api/jobs", body)
    return job_to_automation(payload.get("job") or {}, expert)


def update_automation(automation_id: str, data: dict, expert: bool = False) -> dict:
    body: dict = {}
    if "name" in data and data["name"] is not None:
        body["name"] = str(data["name"]).strip()
    if "instruction" in data and data["instruction"] is not None:
        body["prompt"] = str(data["instruction"])
    if data.get("rhythm"):
        body["schedule"] = rhythm_to_schedule(data["rhythm"])
    if "skills" in data and data["skills"] is not None:
        body["skills"] = data["skills"]
    if data.get("deliver"):
        body["deliver"] = data["deliver"]
    if "status" in data and data["status"] is not None:
        body["enabled"] = data["status"] == "active"
    if not body:
        raise AutomationInvalid("aucune modification fournie")
    payload = _request("PATCH", f"/api/jobs/{automation_id}", body)
    return job_to_automation(payload.get("job") or {}, expert)


def pause_automation(automation_id: str, expert: bool = False) -> dict:
    payload = _request("POST", f"/api/jobs/{automation_id}/pause")
    return job_to_automation(payload.get("job") or {}, expert)


def resume_automation(automation_id: str, expert: bool = False) -> dict:
    payload = _request("POST", f"/api/jobs/{automation_id}/resume")
    return job_to_automation(payload.get("job") or {}, expert)


def run_automation(automation_id: str, expert: bool = False) -> dict:
    payload = _request("POST", f"/api/jobs/{automation_id}/run")
    return job_to_automation(payload.get("job") or {}, expert)


def delete_automation(automation_id: str) -> dict:
    _request("DELETE", f"/api/jobs/{automation_id}")
    return {"ok": True}
