"""Adapter Agents — pilotage des profils Hermes (page Agents, ex-onglet Modèles).

Un « agent » côté produit = un « profil » côté Hermes (``~/.hermes/profiles/<name>/``).
Le profil ``default`` est ``~/.hermes`` lui-même.

Source de vérité = Hermes, piloté par introspection Python (``hermes_cli.profiles``) :
- LISTE  : ``list_profiles`` + ``get_active_profile`` (pointeur « agent de garde », ~/.hermes/active_profile).
- CRÉER  : ``create_profile(clone_config=True)`` — hérite modèle + clés du profil actif, puis SOUL.md custom.
- ACTIVER: ``set_active_profile`` (bascule l'agent de garde).
- SUPPR. : ``delete_profile`` (jamais ``default``).
- MISSION (SOUL.md) : lecture/écriture directe de ``<profil>/SOUL.md``.
- DESCRIPTION : ``write_profile_meta`` (profile.yaml).

On réutilise ``hermes_adapter.introspect``. ``create_profile`` / ``delete_profile`` écrivent sur stdout :
on capture/supprime leur sortie pour ne pas corrompre le JSON renvoyé.
"""

from __future__ import annotations

import json
import re
import unicodedata

from . import hermes_adapter
from .models import Agent


# --- Écriture atomique + verrou, injectés dans les scripts introspectés -------
# Miroir minimal de brain_adapter._write_unlocked/_file_lock (tmp + os.replace, flock),
# réimplémenté ici car ces scripts tournent dans un sous-process isolé (introspect() les
# exécute via ``python -c``) : ils ne peuvent pas importer providers_bridge.brain_adapter.
# Sans ça, un crash pendant l'écriture peut tronquer profile.yaml/config.yaml (finding audit).

_ATOMIC_WRITE_HELPER = """
import os as _os
import tempfile as _tempfile
from contextlib import contextmanager as _contextmanager

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows n'est pas une cible
    _fcntl = None


def _atomic_write_text(path, content):
    \"\"\"Écriture atomique (tmp + os.replace) : jamais de fichier tronqué/vide en cas de coupure.\"\"\"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        _os.replace(tmp, path)
    finally:
        if _os.path.exists(tmp):
            _os.remove(tmp)


@_contextmanager
def _file_lock(path):
    \"\"\"Verrou exclusif (évite un lost-update si deux écritures de profile.yaml se croisent).\"\"\"
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if _fcntl is None:  # pragma: no cover
        yield
        return
    fd = open(lock_path, "a+", encoding="utf-8")
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        yield
    finally:
        try:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
        except OSError:  # pragma: no cover
            pass
        fd.close()
"""


def slugify(display: str) -> str:
    """Transforme un nom d'affichage en identifiant de profil valide (``[a-z0-9][a-z0-9_-]{0,63}``).

    Ex. « Assistant RH » -> « assistant-rh ». Renvoie « agent » en dernier recours.
    """
    s = unicodedata.normalize("NFKD", display or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().strip()).strip("-")[:64]
    if not s or not re.match(r"[a-z0-9]", s):
        s = f"agent-{s}".strip("-") or "agent"
    return s


# --- LISTE --------------------------------------------------------------------

_LIST_SCRIPT = """
import json
from hermes_cli.profiles import list_profiles, get_active_profile, get_profile_dir

try:
    active = get_active_profile()
except Exception:
    active = "default"

def _read_avatar(name):
    # L'avatar est un champ bridge-owned de profile.yaml, absent du moteur Hermes
    # (ProfileInfo/list_profiles ne le connaissent pas) : on le relit nous-mêmes,
    # même fichier que la description, sans toucher au moteur.
    path = get_profile_dir(name) / "profile.yaml"
    if not path.is_file():
        return None
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("avatar")
    return str(value) if value else None

out = []
for p in list_profiles():
    out.append({
        "name": p.name,
        "description": p.description or "",
        "model": p.model,
        "provider": p.provider,
        "is_default": bool(p.is_default),
        "skill_count": int(p.skill_count or 0),
        "gateway_running": bool(p.gateway_running),
        "active": p.name == active,
        "avatar": _read_avatar(p.name),
    })
print(json.dumps(out))
"""


_HOMES_SCRIPT = """
import json
from hermes_cli.profiles import list_profiles, get_profile_dir
print(json.dumps([str(get_profile_dir(p.name)) for p in list_profiles()]))
"""


def profile_homes() -> list[str]:
    """Chemins des dossiers de TOUS les profils (default + nommés).

    Sert à propager une clé d'intégration au ``.env`` de chaque agent (chacun lit le sien ;
    il n'existe pas de ``.env`` global partagé dans Hermes).
    """
    return hermes_adapter.introspect(_HOMES_SCRIPT)


def _normalize_profile_name(name: str) -> str:
    """Miroir de ``hermes_cli.profiles.normalize_profile_name`` (moteur réel) : ``strip()``,
    puis ``"default"`` insensible à la casse/aux espaces, sinon minuscule.

    Sans ce miroir, ``profile_home("Default")``/``profile_home(" rh ")`` divergeait du
    dossier réel que le moteur utilise (finding audit — 404 alors que l'agent existe).
    """
    stripped = (name or "").strip()
    if stripped.casefold() == "default":
        return "default"
    return stripped.lower()


def profile_home(name: str):
    """Dossier d'un profil donné. ``default`` → ``~/.hermes`` ; sinon ``~/.hermes/profiles/<name>``.

    Layout natif de Hermes (cf. hermes_cli.profiles.get_profile_dir). Utilisé pour cibler les
    outils (skills/MCP) d'un agent précis. Le nom est normalisé comme le fait le moteur
    (casse/espaces) pour rester garanti cohérent avec le layout réel sur disque.
    """
    normalized = _normalize_profile_name(name)
    if not normalized or normalized == "default":
        return hermes_adapter.HERMES_HOME
    return hermes_adapter.HERMES_HOME / "profiles" / normalized


def list_agents() -> list[Agent]:
    """Liste les agents (profils Hermes) avec leur état (dont l'agent actif)."""
    raw = hermes_adapter.introspect(_LIST_SCRIPT)
    return [
        Agent(
            name=it["name"],
            description=it.get("description", "") or "",
            model=it.get("model"),
            provider=it.get("provider"),
            is_default=bool(it.get("is_default", False)),
            skill_count=int(it.get("skill_count", 0) or 0),
            gateway_running=bool(it.get("gateway_running", False)),
            active=bool(it.get("active", False)),
            avatar=it.get("avatar"),
        )
        for it in raw
    ]


# --- CRÉER --------------------------------------------------------------------
# clone_config=True : le nouvel agent hérite du modèle + des clés API du profil actif
# (sinon il ne pourrait pas répondre). no_alias=True : pas de wrapper shell dans le PATH.

_CREATE_SCRIPT = _ATOMIC_WRITE_HELPER + """
import io, json, contextlib
from hermes_cli.profiles import create_profile, get_profile_dir

name = {name}
description = {description}
soul = {soul}
avatar = {avatar}

buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        create_profile(name, clone_config=True, no_alias=True, description=description)
except FileExistsError:
    print(json.dumps({{"ok": False, "error": "exists"}}))
except Exception as exc:
    print(json.dumps({{"ok": False, "error": str(exc)[:200]}}))
else:
    if soul:
        # SOUL.md = le prompt système de l'agent, le fichier le plus sensible du profil :
        # une coupure pendant l'écriture ne doit jamais le laisser tronqué/vide (cf.
        # profile.yaml/config.yaml ci-dessous, même garantie tmp+os.replace).
        soul_path = get_profile_dir(name) / "SOUL.md"
        with _file_lock(soul_path):
            _atomic_write_text(soul_path, soul)
    if avatar:
        # Champ bridge-owned, absent de write_profile_meta (moteur) : on l'écrit
        # nous-mêmes dans profile.yaml, en préservant le reste du fichier.
        import yaml
        path = get_profile_dir(name) / "profile.yaml"
        with _file_lock(path):
            existing = {{}}
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded = yaml.safe_load(f) or {{}}
                    if isinstance(loaded, dict):
                        existing = loaded
                except Exception:
                    existing = {{}}
            existing["avatar"] = avatar
            _atomic_write_text(path, yaml.safe_dump(existing, sort_keys=False, default_flow_style=False))
    print(json.dumps({{"ok": True, "name": name}}))
"""


def create_agent(name: str, description: str = "", soul: str = "", avatar: str | None = None) -> dict:
    """Crée un agent (profil). ``name`` est un nom d'affichage, slugifié en identifiant.

    ``avatar`` optionnel : nom de fichier d'avatar persisté dans profile.yaml (même pattern
    que ``description``, zéro traitement d'image côté bridge).
    Renvoie ``{"ok": True, "name": <slug>}`` ou ``{"ok": False, "error": "exists"|...}``.
    """
    slug = slugify(name)
    script = _CREATE_SCRIPT.format(
        name=json.dumps(slug),
        description=json.dumps(description or ""),
        soul=json.dumps(soul or ""),
        # json.dumps(None) -> "null" (invalide en Python) : on injecte le littéral None.
        avatar=json.dumps(avatar) if avatar is not None else "None",
    )
    return hermes_adapter.introspect(script, timeout=120)


# --- ACTIVER ------------------------------------------------------------------

_ACTIVATE_SCRIPT = """
import json
from hermes_cli.profiles import set_active_profile, profile_exists

name = {name}
if name != "default" and not profile_exists(name):
    print(json.dumps({{"found": False}}))
else:
    set_active_profile(name)
    print(json.dumps({{"found": True, "ok": True}}))
"""


def set_active_agent(name: str) -> bool:
    """Bascule l'agent « de garde ». Renvoie False si l'agent est inconnu (404)."""
    script = _ACTIVATE_SCRIPT.format(name=json.dumps(name))
    return bool(hermes_adapter.introspect(script).get("found"))


# --- SUPPRIMER ----------------------------------------------------------------

_DELETE_SCRIPT = """
import io, json, contextlib
from hermes_cli.profiles import delete_profile, profile_exists, get_active_profile

name = {name}
if name == "default":
    print(json.dumps({{"found": True, "ok": False, "error": "default"}}))
elif not profile_exists(name):
    print(json.dumps({{"found": False}}))
else:
    try:
        active = get_active_profile()
    except Exception:
        active = "default"
    if name == active:
        # L'agent de garde ne doit jamais pointer dans le vide : le moteur ne réinitialise
        # pas ~/.hermes/active_profile quand son dossier disparaît (finding audit).
        print(json.dumps({{"found": True, "ok": False, "error": "active"}}))
    else:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            delete_profile(name, yes=True)
        print(json.dumps({{"found": True, "ok": True}}))
"""


def delete_agent(name: str) -> dict:
    """Supprime un agent. Renvoie ``{"found": bool, "ok"?: bool, "error"?: "default"|"active"}``.

    Refuse la suppression de l'agent actuellement actif (« agent de garde ») : le supprimer
    laisserait ``~/.hermes/active_profile`` pointer sur un dossier qui n'existe plus.
    """
    script = _DELETE_SCRIPT.format(name=json.dumps(name))
    return hermes_adapter.introspect(script)


# --- MISSION (SOUL.md) --------------------------------------------------------

_GET_SOUL_SCRIPT = """
import json
from hermes_cli.profiles import get_profile_dir, profile_exists

name = {name}
if name != "default" and not profile_exists(name):
    print(json.dumps({{"found": False}}))
else:
    path = get_profile_dir(name) / "SOUL.md"
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    print(json.dumps({{"found": True, "content": content}}))
"""

_SET_SOUL_SCRIPT = _ATOMIC_WRITE_HELPER + """
import json
from hermes_cli.profiles import get_profile_dir, profile_exists

name = {name}
content = {content}
if name != "default" and not profile_exists(name):
    print(json.dumps({{"found": False}}))
else:
    # Édition manuelle de la mission : même garantie tmp+os.replace que la création
    # (finding audit MAJEUR — un crash pendant l'écriture ne doit jamais tronquer le
    # prompt système en place, le fichier le plus sensible d'un profil).
    path = get_profile_dir(name) / "SOUL.md"
    with _file_lock(path):
        _atomic_write_text(path, content)
    print(json.dumps({{"found": True, "ok": True}}))
"""


def get_agent_soul(name: str) -> str | None:
    """Lit la mission (SOUL.md) d'un agent. Renvoie None si l'agent est inconnu."""
    script = _GET_SOUL_SCRIPT.format(name=json.dumps(name))
    res = hermes_adapter.introspect(script)
    return res.get("content") if res.get("found") else None


def set_agent_soul(name: str, content: str) -> bool:
    """Écrit la mission (SOUL.md). Renvoie False si l'agent est inconnu (404)."""
    script = _SET_SOUL_SCRIPT.format(name=json.dumps(name), content=json.dumps(content or ""))
    return bool(hermes_adapter.introspect(script).get("found"))


# --- DESCRIPTION (profile.yaml) ----------------------------------------------

_SET_DESC_SCRIPT = """
import json
from hermes_cli.profiles import get_profile_dir, write_profile_meta, profile_exists

name = {name}
description = {description}
if name != "default" and not profile_exists(name):
    print(json.dumps({{"found": False}}))
else:
    write_profile_meta(get_profile_dir(name), description=description, description_auto=False)
    print(json.dumps({{"found": True, "ok": True}}))
"""


def set_agent_description(name: str, description: str) -> bool:
    """Met à jour la description (profile.yaml). Renvoie False si l'agent est inconnu (404)."""
    script = _SET_DESC_SCRIPT.format(name=json.dumps(name), description=json.dumps(description or ""))
    return bool(hermes_adapter.introspect(script).get("found"))


# --- AVATAR (profile.yaml) -----------------------------------------------------
# Champ bridge-owned : ``write_profile_meta`` (moteur Hermes) ne connaît que
# description/description_auto, donc on lit/écrit "avatar" nous-mêmes dans le
# même fichier, en préservant les autres clés (zéro modif du moteur Hermes).

_SET_AVATAR_SCRIPT = _ATOMIC_WRITE_HELPER + """
import json
from hermes_cli.profiles import get_profile_dir, profile_exists

name = {name}
avatar = {avatar}
if name != "default" and not profile_exists(name):
    print(json.dumps({{"found": False}}))
else:
    import yaml
    path = get_profile_dir(name) / "profile.yaml"
    with _file_lock(path):
        existing = {{}}
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {{}}
                if isinstance(loaded, dict):
                    existing = loaded
            except Exception:
                existing = {{}}
        if avatar is None:
            existing.pop("avatar", None)
        else:
            existing["avatar"] = avatar
        _atomic_write_text(path, yaml.safe_dump(existing, sort_keys=False, default_flow_style=False))
    print(json.dumps({{"found": True, "ok": True}}))
"""


def set_agent_avatar(name: str, avatar: str | None) -> bool:
    """Met à jour l'avatar (profile.yaml) d'un agent. Renvoie False si l'agent est inconnu (404).

    ``avatar`` est une simple chaîne (nom de fichier ou chemin relatif) ; ``None`` retire le
    champ (désélection). Zéro traitement d'image côté bridge.
    """
    # json.dumps(None) -> "null" (invalide en Python) : on injecte le littéral None.
    avatar_lit = json.dumps(avatar) if avatar is not None else "None"
    script = _SET_AVATAR_SCRIPT.format(name=json.dumps(name), avatar=avatar_lit)
    return bool(hermes_adapter.introspect(script).get("found"))


# --- ROSTER (la « carte des troupes » de l'orchestrateur) --------------------
# Un orchestrateur (ex. Mike) doit connaître dynamiquement les agents existants
# (identifiant + rôle) pour router les tâches via le Kanban, et ne JAMAIS inventer
# un identifiant absent (sinon la tâche part en `skipped_nonspawnable`, silencieusement).
#
# On injecte un bloc géré entre marqueurs dans le SOUL de tout profil qui les contient.
# Tout reste côté bridge : on ne touche ni au moteur Hermes ni au flux chat temps réel.

ROSTER_BEGIN = "<!-- AGENTS:DEBUT -->"
ROSTER_END = "<!-- AGENTS:FIN -->"

_MAX_DESC = 200  # on tronque les descriptions longues pour garder le bloc lisible


def build_roster_block(agents: list[Agent], exclude: str | None = None) -> str:
    """Construit le bloc « équipe » (entre marqueurs) listant les agents mobilisables.

    ``exclude`` = identifiant de l'orchestrateur lui-même (il ne se liste pas).
    Fonction pure et déterministe — testable sans Hermes.
    """
    others = [a for a in agents if a.name != exclude]
    lines = [
        ROSTER_BEGIN,
        "## Ton équipe (agents que tu peux mobiliser)",
        "",
        "_Liste tenue à jour automatiquement — ne la modifie pas à la main._",
        "",
    ]
    if others:
        lines.append(
            "Tu confies une tâche UNIQUEMENT à l'un de ces agents, en reprenant son "
            "identifiant exact (entre `accents graves`) comme assignee Kanban :"
        )
        lines.append("")
        for a in others:
            desc = " ".join((a.description or "").split())
            if len(desc) > _MAX_DESC:
                desc = desc[: _MAX_DESC - 1].rstrip() + "…"
            lines.append(f"- `{a.name}` — {desc}" if desc else f"- `{a.name}`")
        lines.append("")
        lines.append(
            "Si aucun agent de cette liste ne convient, dis-le au dirigeant et propose "
            "d'en créer un. N'invente JAMAIS un identifiant d'agent absent de cette liste : "
            "une tâche assignée à un agent inexistant n'est jamais exécutée."
        )
    else:
        lines.append(
            "Aucun autre agent n'est disponible pour l'instant. Si une tâche dépasse ton "
            "périmètre, propose au dirigeant d'en créer un — n'invente jamais un agent."
        )
    lines.append(ROSTER_END)
    return "\n".join(lines)


def _has_roster_markers(soul: str) -> bool:
    return ROSTER_BEGIN in soul and ROSTER_END in soul


def replace_roster_block(soul: str, block: str) -> str:
    """Remplace le contenu entre marqueurs par ``block``. No-op si les marqueurs manquent.

    Ne touche QUE la zone entre marqueurs : ce que le dirigeant a rédigé est préservé.
    """
    if not _has_roster_markers(soul):
        return soul
    if soul.count(ROSTER_BEGIN) > 1 or soul.count(ROSTER_END) > 1:
        # Marqueurs dupliqués (ex. copier-coller manuel du dirigeant) : on refuse de toucher
        # au fichier plutôt que de risquer de tronquer un contenu légitime entre deux paires.
        return soul
    start = soul.index(ROSTER_BEGIN)
    end = soul.index(ROSTER_END) + len(ROSTER_END)
    if end <= start:
        return soul
    return soul[:start] + block + soul[end:]


_READ_ALL_SOULS_SCRIPT = """
import json
from hermes_cli.profiles import list_profiles, get_profile_dir

out = {}
for p in list_profiles():
    path = get_profile_dir(p.name) / "SOUL.md"
    out[p.name] = path.read_text(encoding="utf-8") if path.exists() else ""
print(json.dumps(out))
"""


_WRITE_SOULS_SCRIPT = _ATOMIC_WRITE_HELPER + """
import json
from hermes_cli.profiles import get_profile_dir, profile_exists

updates = {updates}
written = []
for name, content in updates.items():
    if name == "default" or profile_exists(name):
        # Resync de flotte (boucle sur tous les profils) : c'est le mécanisme qui a déjà
        # causé une dérive de 3 SOUL.md sur 6 (collage manuel du 30/06) — un crash en
        # cours de boucle ne doit jamais tronquer le SOUL.md du profil en cours d'écriture.
        path = get_profile_dir(name) / "SOUL.md"
        with _file_lock(path):
            _atomic_write_text(path, content)
        written.append(name)
print(json.dumps({{"written": written}}))
"""


def _read_all_souls() -> dict:
    """Lit le SOUL.md de TOUS les profils en un seul appel (``{name: contenu}``)."""
    return hermes_adapter.introspect(_READ_ALL_SOULS_SCRIPT)


def _write_souls(mapping: dict) -> list:
    """Écrit les SOUL.md modifiés en un seul appel. Renvoie la liste des profils écrits."""
    if not mapping:
        return []
    script = _WRITE_SOULS_SCRIPT.format(updates=json.dumps(mapping))
    return hermes_adapter.introspect(script, timeout=120).get("written", [])


def sync_orchestrator_roster() -> dict:
    """Met à jour le bloc « équipe » dans le SOUL de chaque orchestrateur.

    Un orchestrateur = un profil dont le SOUL contient les marqueurs roster. Sa liste
    est reconstruite depuis les agents existants (en s'excluant lui-même). Idempotent.
    Renvoie ``{"updated": [<noms réécrits>]}``.
    """
    agents = list_agents()
    souls = _read_all_souls()
    updates = {}
    for name, soul in souls.items():
        if not _has_roster_markers(soul):
            continue
        new_soul = replace_roster_block(soul, build_roster_block(agents, exclude=name))
        if new_soul != soul:
            updates[name] = new_soul
    return {"updated": _write_souls(updates)}


# --- CERVEAU PARTAGÉ (propagation du provider actif à toute l'équipe) ----------
# « Un dirigeant = un assistant » : le cerveau (provider/modèle) que le client choisit
# dans le sélecteur vaut pour Mike ET pour tous les agents qu'il mobilise. Sans ça, les
# agents restent figés sur leur provider de création ; si ce provider est déconnecté
# ensuite (ex. Codex), leurs workers Kanban échouent silencieusement (crash à l'auth).
# Le profil ``default`` (= Mike) est déjà réglé par ``hermes_adapter.set_active`` ; ici
# on aligne uniquement les profils nommés.

_PROPAGATE_BRAIN_SCRIPT = _ATOMIC_WRITE_HELPER + """
import json, yaml
from hermes_cli.profiles import list_profiles, get_profile_dir

provider = {provider}
model = {model}
base_url = {base_url}

updated = []
for p in list_profiles():
    if p.is_default:
        continue
    path = get_profile_dir(p.name) / "config.yaml"
    if not path.is_file():
        continue
    with _file_lock(path):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {{}}
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        mb = dict(data.get("model") or {{}})
        mb["provider"] = provider
        mb["default"] = model
        if base_url:
            mb["base_url"] = base_url
        data["model"] = mb
        _atomic_write_text(path, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        updated.append(p.name)
print(json.dumps({{"updated": updated}}))
"""


def propagate_brain_to_agents(provider: str, model: str, base_url: str | None = None) -> list[str]:
    """Aligne le cerveau (provider/modèle/base_url) de tous les agents nommés sur le
    cerveau actif. Best-effort ; renvoie la liste des agents mis à jour."""
    script = _PROPAGATE_BRAIN_SCRIPT.format(
        provider=json.dumps(provider),
        model=json.dumps(model),
        # json.dumps(None) -> "null" (invalide en Python) : on injecte le littéral None.
        base_url=json.dumps(base_url) if base_url is not None else "None",
    )
    return hermes_adapter.introspect(script, timeout=60).get("updated", [])
