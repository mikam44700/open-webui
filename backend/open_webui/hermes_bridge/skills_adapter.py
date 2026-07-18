"""Adapter Compétences — pilotage des skills natives de Hermes (page Capacités, onglet Compétences).

Source de vérité = Hermes :
- LISTE : introspection via ``tools.skills_tool._find_all_skills`` (dossiers ``~/.hermes/skills/``).
- TOGGLE : ``get_disabled_skills`` / ``save_disabled_skills`` (clé ``skills.disabled`` de config.yaml).

Choix : on pilote les skills au niveau GLOBAL (``skills.disabled``, toutes plateformes) — plus simple
et cohérent entre liste et toggle qu'un pilotage par plateforme. On réutilise ``hermes_adapter.introspect``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import fsutil, hermes_adapter, profiles_adapter
from .models import CustomSkill, Skill

# Liste toutes les skills découvertes + leur état (désactivée globalement ou non).
_LIST_SCRIPT = """
import json
from hermes_cli.config import load_config
from hermes_cli.skills_config import get_disabled_skills
from tools.skills_tool import _find_all_skills

config = load_config()
disabled = set(get_disabled_skills(config))
out = []
for s in _find_all_skills(skip_disabled=True):
    name = s.get("name")
    if not name:
        continue
    out.append({
        "name": name,
        "category": s.get("category"),
        "description": s.get("description", "") or "",
        "enabled": name not in disabled,
    })
print(json.dumps(out))
"""

# Active/désactive une skill (membership dans ``skills.disabled``).
_TOGGLE_SCRIPT = """
import json
from hermes_cli.config import load_config
from hermes_cli.skills_config import get_disabled_skills, save_disabled_skills
from tools.skills_tool import _find_all_skills

name = {name}
enabled = {enabled}
known = {{s.get("name") for s in _find_all_skills(skip_disabled=True)}}
if name not in known:
    print(json.dumps({{"found": False}}))
else:
    config = load_config()
    disabled = set(get_disabled_skills(config))
    if enabled:
        disabled.discard(name)
    else:
        disabled.add(name)
    save_disabled_skills(config, disabled)
    print(json.dumps({{"found": True, "ok": True}}))
"""


def list_skills(hermes_home=None) -> list[Skill]:
    """Liste les compétences natives Hermes avec leur état (activée/désactivée).

    ``hermes_home`` cible un profil précis (état des skills PAR AGENT) ; None = profil courant.
    """
    raw = hermes_adapter.introspect(_LIST_SCRIPT, hermes_home=hermes_home)
    return [
        Skill(
            name=it["name"],
            category=it.get("category"),
            description=it.get("description", ""),
            enabled=bool(it.get("enabled", True)),
        )
        for it in raw
    ]


def set_skill_enabled(name: str, enabled: bool, hermes_home=None) -> bool:
    """Active/désactive une compétence (pour le profil ciblé). False si la skill est inconnue (404)."""
    # Littéral Python (True/False), PAS json.dumps qui produit "true"/"false" (invalide en Python).
    script = _TOGGLE_SCRIPT.format(name=json.dumps(name), enabled=("True" if enabled else "False"))
    result = hermes_adapter.introspect(script, hermes_home=hermes_home)
    return bool(result.get("found"))


# --- COMPÉTENCES « MAISON » (sur mesure, créées par le client) ---------------
# Nos compétences vivent dans ``~/.hermes/skills/maison/<slug>/SKILL.md`` : ce sont de
# vraies skills Hermes (donc chargées par le moteur), mais rangées dans un dossier dédié
# qui permet de ne lister QUE les nôtres (page « Compétences » de l'Espace de travail).
# Tout est filesystem côté bridge — pas d'introspection Hermes pour créer/lister/supprimer.

MAISON_DIRNAME = "maison"


def _maison_dir() -> Path:
    """Dossier des compétences maison (``~/.hermes/skills/maison``)."""
    return hermes_adapter.HERMES_HOME / "skills" / MAISON_DIRNAME


# Noms des compétences désactivées globalement (clé skills.disabled). Best-effort.
_DISABLED_SCRIPT = """
import json
from hermes_cli.config import load_config
from hermes_cli.skills_config import get_disabled_skills
print(json.dumps(list(get_disabled_skills(load_config()))))
"""


def _disabled_skill_names() -> set:
    """Ensemble des compétences désactivées dans le moteur. Vide si Hermes injoignable (tout actif)."""
    try:
        return set(hermes_adapter.introspect(_DISABLED_SCRIPT) or [])
    except Exception:  # noqa: BLE001 — tolérant : à défaut, on considère tout actif
        return set()


def render_skill_md(
    slug: str, label: str, description: str, instructions: str, category: str = "Autres"
) -> str:
    """Construit le contenu d'un ``SKILL.md`` au format AgentSkills (frontmatter + corps).

    La description est ramenée sur UNE ligne (JSON) pour ne jamais casser le YAML.
    ``category`` range la compétence dans la page (Vente, Finance, SAV…). Fonction pure.
    """
    desc_one_line = " ".join((description or "").split())
    cat = (category or "Autres").strip() or "Autres"
    body = (instructions or "").strip()
    return (
        "---\n"
        f"name: {slug}\n"
        f"description: {json.dumps(desc_one_line, ensure_ascii=False)}\n"
        f"category: {json.dumps(cat, ensure_ascii=False)}\n"
        "version: 1.0.0\n"
        "metadata:\n"
        "  agentos:\n"
        "    custom: true\n"
        "---\n"
        "\n"
        f"# {label}\n"
        "\n"
        f"{body}\n"
    )


def parse_custom_skill(text: str) -> dict:
    """Relit le libellé (titre ``#`` du corps) et la description (frontmatter) d'un SKILL.md.

    Tolérant : renvoie des chaînes vides si les champs manquent.
    """
    label = ""
    description = ""
    category = "Autres"
    parts = text.split("---", 2)
    frontmatter = parts[1] if len(parts) >= 3 else ""
    body = parts[2] if len(parts) >= 3 else text
    for line in frontmatter.splitlines():
        if line.startswith("description:"):
            raw = line[len("description:") :].strip()
            try:
                description = json.loads(raw)
            except (ValueError, json.JSONDecodeError):
                description = raw.strip('"')
        elif line.startswith("category:"):
            raw = line[len("category:") :].strip()
            try:
                category = json.loads(raw) or "Autres"
            except (ValueError, json.JSONDecodeError):
                category = raw.strip('"') or "Autres"
    instructions = ""
    body_lines = body.splitlines()
    for i, line in enumerate(body_lines):
        if line.startswith("# "):
            label = line[2:].strip()
            instructions = "\n".join(body_lines[i + 1 :]).strip()
            break
    return {
        "label": label,
        "description": description,
        "category": category,
        "instructions": instructions,
    }


def list_custom_skills() -> list[CustomSkill]:
    """Liste les compétences maison (dossiers ``maison/<slug>/`` contenant un SKILL.md)."""
    base = _maison_dir()
    if not base.is_dir():
        return []
    disabled = _disabled_skill_names()
    out: list[CustomSkill] = []
    for child in sorted(base.iterdir()):
        if child.name.startswith("."):
            continue  # dossiers cachés (dont la corbeille ".trash") — jamais des compétences
        skill_md = child / "SKILL.md"
        if not (child.is_dir() and skill_md.exists()):
            continue
        parsed = parse_custom_skill(skill_md.read_text(encoding="utf-8"))
        out.append(
            CustomSkill(
                name=child.name,
                label=parsed["label"] or child.name,
                description=parsed["description"],
                category=parsed.get("category") or "Autres",
                enabled=child.name not in disabled,
            )
        )
    out.sort(key=lambda s: (s.category.lower(), s.label.lower()))
    return out


def get_custom_skill(name: str) -> dict | None:
    """Renvoie le contenu COMPLET d'une compétence maison (dont les instructions).

    None si inconnue ou si le nom sort du dossier maison (anti-traversal).
    """
    base = _maison_dir()
    target = (base / name).resolve()
    if target.parent != base.resolve():
        return None
    skill_md = target / "SKILL.md"
    if not skill_md.exists():
        return None
    parsed = parse_custom_skill(skill_md.read_text(encoding="utf-8"))
    return {
        "name": name,
        "label": parsed["label"] or name,
        "description": parsed["description"],
        "category": parsed.get("category") or "Autres",
        "instructions": parsed.get("instructions", ""),
    }


def create_custom_skill(
    label: str, description: str = "", instructions: str = "", category: str = "Autres"
) -> dict:
    """Crée une compétence maison. ``label`` est un nom d'affichage, slugifié en identifiant.

    Renvoie ``{"ok": True, "name": <slug>}`` ou ``{"ok": False, "error": "exists"}``.

    Création atomique côté filesystem (``mkdir`` sans ``exist_ok``, sans ``exists()`` préalable) :
    sous concurrence (double-clic, deux requêtes simultanées sur le même libellé), un seul appel
    peut réussir — l'autre reçoit ``exists`` et n'écrase JAMAIS le SKILL.md du premier (l'ancien
    code faisait ``exists()`` puis ``mkdir(exist_ok=True)``, un TOCTOU qui pouvait laisser les deux
    appels réussir en s'écrasant l'un l'autre).
    """
    slug = profiles_adapter.slugify(label)
    target = _maison_dir() / slug
    try:
        target.mkdir(parents=True)
    except FileExistsError:
        return {"ok": False, "error": "exists"}
    (target / "SKILL.md").write_text(
        render_skill_md(slug, label, description, instructions, category), encoding="utf-8"
    )
    return {"ok": True, "name": slug}


# --- Corbeille des compétences maison supprimées ------------------------------
# Cohérent avec la règle produit de non-destruction déjà en place pour le coffre Obsidian
# (memory_adapter._trash_root / vault-guard) : une suppression déplace vers une corbeille au lieu
# de détruire définitivement (``rmtree``). Pas de purge automatique, pas de TTL.

_TRASH_DIRNAME = ".trash"
_TRASH_MANIFEST_NAME = ".trash-manifest.json"


def _trash_dir() -> Path:
    """Corbeille des compétences maison (``maison/.trash``), créée à la demande."""
    trash = _maison_dir() / _TRASH_DIRNAME
    trash.mkdir(parents=True, exist_ok=True)
    return trash


def _trash_manifest_path() -> Path:
    return _trash_dir() / _TRASH_MANIFEST_NAME


def _read_trash_manifest() -> list[dict]:
    path = _trash_manifest_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError):
        return []


def _write_trash_manifest(entries: list[dict]) -> None:
    # Écriture atomique (tmp + os.replace) : le manifeste est la source de vérité de la
    # corbeille, il ne doit jamais être tronqué par une coupure en cours d'écriture.
    fsutil.atomic_write_text(_trash_manifest_path(), json.dumps(entries, ensure_ascii=False))


def _record_trash(trash_ref: str, original_name: str) -> None:
    """Ajoute une entrée au manifeste de corbeille (source de vérité, ``ref`` = nom sur disque)."""
    entries = [e for e in _read_trash_manifest() if e.get("ref") != trash_ref]
    entries.append({"ref": trash_ref, "name": original_name, "deleted_at": time.time()})
    _write_trash_manifest(entries)


def delete_custom_skill(name: str) -> dict:
    """Supprime DOUCEMENT une compétence maison : déplacée vers la corbeille (récupérable), jamais
    détruite définitivement (pas de ``rmtree``).

    Renvoie ``{"found": False}`` si le nom est inconnu, sort du dossier maison (anti-traversal),
    ou vise un dossier caché (la corbeille elle-même comprise).
    """
    if not name or name.startswith("."):
        return {"found": False}
    base = _maison_dir()
    target = (base / name).resolve()
    if target.parent != base.resolve() or not target.is_dir():
        return {"found": False}
    trash = _trash_dir()
    dest = trash / name
    counter = 2
    while dest.exists():
        dest = trash / f"{name}-{counter}"
        counter += 1
    target.rename(dest)
    _record_trash(dest.name, name)
    return {"found": True, "ok": True}


class RestoreConflict(Exception):
    """La restauration écraserait une compétence maison déjà présente sous ce nom."""


def _trashed_skill_path(trash_ref: str) -> Path:
    """Résout une réf. de corbeille en chemin, CONFINÉ à ``maison/.trash`` (anti path traversal).

    Miroir de ``memory_adapter._trashed_path`` : une réf. bricolée (``../autre-skill``) ne doit
    jamais pouvoir atteindre une compétence maison active, ni sortir du dossier maison.
    """
    trash = _trash_dir()
    src = (trash / trash_ref).resolve()
    if trash.resolve() not in src.parents:
        raise ValueError("bad trash ref")
    return src


def list_custom_skills_trash() -> list[dict]:
    """Corbeille des compétences maison, récupérables (les plus récentes d'abord).

    Miroir de ``memory_adapter.list_trash`` : ne montre que les entrées dont le dossier existe
    encore réellement sur disque (auto-nettoyage des références orphelines du manifeste).
    """
    trash = _trash_dir()
    manifest = _read_trash_manifest()
    kept = [e for e in manifest if e.get("ref") and (trash / e["ref"]).is_dir()]
    if len(kept) != len(manifest):
        _write_trash_manifest(kept)  # purge des références orphelines
    kept.sort(key=lambda e: e.get("deleted_at", 0.0), reverse=True)
    return kept


def restore_custom_skill(trash_ref: str) -> dict:
    """Restaure une compétence maison depuis la corbeille vers ``maison/<nom_original>``.

    Symétrique de ``delete_custom_skill`` : ferme le finding audit MOYENNE (« corbeille
    récupérable » sans aucun chemin de récupération) — miroir de
    ``memory_adapter.restore_note``/``restore_folder`` pour le coffre Obsidian.

    Renvoie ``{"ok": True, "name": <nom>}``. Lève ``FileNotFoundError`` si ``trash_ref`` est
    inconnue, ``RestoreConflict`` si une compétence porte déjà ce nom (jamais d'écrasement
    silencieux — même règle de non-destruction que le coffre).
    """
    src = _trashed_skill_path(trash_ref)
    if not src.is_dir():
        raise FileNotFoundError(trash_ref)
    manifest = _read_trash_manifest()
    entry = next((e for e in manifest if e.get("ref") == trash_ref), None)
    original_name = (entry or {}).get("name") or src.name
    dest = _maison_dir() / original_name
    if dest.exists():
        raise RestoreConflict(original_name)
    src.rename(dest)
    _write_trash_manifest([e for e in manifest if e.get("ref") != trash_ref])
    return {"ok": True, "name": original_name}
