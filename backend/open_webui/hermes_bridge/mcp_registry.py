"""Registre MCP distant (fathah/hermes-registry) — « re-pomper le registre ».

On lit le ``index.json`` public (les ~55 MCP) puis, pour chaque MCP, son ``manifest.json``
(transport, url, configSchema) afin de savoir comment l'installer :

- ``remote``      : serveur http/sse distant → installable en 1 clic (connexion par compte,
                    pattern HubSpot : on l'ajoute en custom http + OAuth).
- ``local_app``   : serveur http sur 127.0.0.1 → nécessite une app locale (ex. Figma desktop).
- ``stdio_key``   : commande locale (npx…) avec clé(s) requise(s) → formulaire de clés (ultérieur).
- ``stdio_plain`` : commande locale sans clé → lancement direct (ultérieur).

Robustesse : résultat enrichi mis en cache (TTL court) ; toute erreur réseau dégrade
proprement (entrée non installable, jamais d'écran cassé).
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import re
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

_logger = logging.getLogger(__name__)

# Registre public (fathah/hermes-registry), épinglé sur un commit SHA précis plutôt que sur
# la branche mobile ``main`` (finding HAUTE #3 : un registre non signé — la seule protection
# côté intégrité doit être qu'un push malveillant sur ``main`` ne peut PAS changer le contenu
# servi sous nos pieds entre deux déploiements du bridge). Mise à jour : relire le diff du
# registre distant (``git log`` côté hermes-registry) avant de faire avancer ce SHA.
_PINNED_REGISTRY_COMMIT = "9eac45a2beba230414b9bcf2041b5ff407d3c935"  # 2026-07-09, vérifié manuellement
_RAW_BASE = f"https://raw.githubusercontent.com/fathah/hermes-registry/{_PINNED_REGISTRY_COMMIT}/"
_INDEX_URL = _RAW_BASE + "index.json"

_CACHE_TTL_S = 1800  # 30 min ; au-delà on sert le cache + on rafraîchit en arrière-plan
_FETCH_TIMEOUT_S = 8
_MANIFEST_WORKERS = 16
_FETCH_ATTEMPTS = 2  # un manifest qui échoue (flake réseau) ne doit pas déclasser le MCP

# Cache mémoire : (timestamp_monotonic, entries_enrichies). Doublé d'un cache disque pour
# survivre aux redémarrages, et rafraîchi en arrière-plan (l'utilisateur n'attend jamais).
_cache: tuple[float, list[dict]] | None = None
_lock = threading.Lock()
_refreshing = False

# Un id de connecteur (registre distant, non signé) devient une clé de config.yaml ET
# potentiellement un composant de chemin de fichier (purge des tokens OAuth) : charset sûr
# uniquement, jamais de "/" ou ".." (défense en profondeur, cf. finding HAUTE #1).
_SAFE_ID_RE = re.compile(r"^[a-z0-9_-]+$")


def _http_get_json(url: str, timeout: int) -> object:
    """GET JSON via la stdlib (aucune dépendance ajoutée). Séparé pour être mockable en test.

    HTTPS strict (finding HAUTE #3, défense en profondeur) : ``_RAW_BASE`` est une constante
    https en dur, mais on refuse explicitement tout downgrade au point de fetch — un futur
    refactor qui construirait une URL différemment (ou un MITM qui redirigerait vers du http)
    ne doit jamais pouvoir faire passer une requête en clair.
    """
    if not url.lower().startswith("https://"):
        raise ValueError(f"URL non-HTTPS refusée (registre MCP) : {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": "agent-os-bridge"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (HTTPS forcé ci-dessus)
        if not resp.geturl().lower().startswith("https://"):
            raise ValueError("redirection hors HTTPS refusée (registre MCP)")
        return json.loads(resp.read().decode("utf-8"))


def _get_json_retry(url: str, attempts: int = _FETCH_ATTEMPTS) -> object:
    """``_http_get_json`` avec quelques tentatives — absorbe les flakes réseau de GitHub raw.

    Relève la dernière exception si toutes les tentatives échouent (l'appelant décide du repli).
    """
    last_exc: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            return _http_get_json(url, _FETCH_TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001 — on retente quelle que soit l'erreur réseau
            last_exc = exc
    raise last_exc if last_exc is not None else RuntimeError("échec de récupération")


def _icon_url(path: str | None) -> str | None:
    """Construit l'URL absolue du logo d'un MCP à partir de son chemin relatif dans le registre."""
    path = (path or "").strip()
    return _RAW_BASE + path if path else None


def _to_entry(item: dict) -> dict | None:
    """Normalise une entrée brute de l'index en métadonnées d'affichage. None si invalide."""
    entry_id = str(item.get("id") or "").strip().lower()
    if not entry_id or not _SAFE_ID_RE.match(entry_id):
        return None
    return {
        "id": entry_id,
        "label": str(item.get("name") or entry_id),
        "description": str(item.get("description") or ""),
        "icon_url": _icon_url(item.get("icon")),
        "source_url": item.get("source"),
        "tags": [str(t) for t in (item.get("tags") or [])],
        "_path": str(item.get("path") or ""),  # interne : pour récupérer le manifest
    }


def _parse_index(data: object) -> list[dict]:
    """Extrait les MCP (``type == "mcp"``) d'un index de registre, sous forme normalisée."""
    items = data if isinstance(data, list) else (data or {}).get("entries", [])
    entries = []
    for it in items:
        if not isinstance(it, dict) or it.get("type") != "mcp":
            continue
        entry = _to_entry(it)
        if entry is not None:
            entries.append(entry)
    return entries


def _is_localhost(url: str | None) -> bool:
    """Détecte un hôte local en parsant l'URL (pas une sous-chaîne brute, finding BASSE #6).

    Une URL distante légitime contenant "127.0.0.1"/"localhost" ailleurs que dans l'hôte
    (ex. un paramètre de requête, un sous-domaine) ne doit pas être classée locale.
    """
    if not url:
        return False
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return False
    return host in ("127.0.0.1", "localhost")


# Lanceurs stdio attendus pour un MCP (finding HAUTE #3 : le registre distant n'est ni signé
# ni vérifié par checksum). Liste volontairement courte : les runtimes réellement utilisés par
# les manifests stdio du registre (npx/uvx/node/python...), rien d'autre.
#
# LIMITE INTRINSÈQUE, à ne jamais perdre de vue (grill audit phase 3, HAUTE nuancée) : cette
# allowlist réduit la SURFACE d'attaque (elle empêche un manifest de lancer un binaire hors
# liste, ou d'échapper vers un shell), mais elle NE PEUT PAS empêcher l'exécution de code par
# les commandes elles-mêmes. `node`, `python`/`python3`, `docker`, `deno`, `bunx`, `uv`, `pnpm`
# sont des interpréteurs/lanceurs Turing-complets PAR CONSTRUCTION : un manifest parfaitement
# conforme à l'allowlist (`command="node"`, `args=["-e", "<code arbitraire>"]`) reste une RCE
# complète — aucun filtre d'arguments raisonnable ne peut fermer ce trou sans réécrire un
# interpréteur JS/Python maison. Ce n'est pas un oubli, c'est la nature d'un serveur MCP stdio :
# il EST du code exécuté en subprocess par construction.
#
# La VRAIE garantie de sécurité ici n'est donc PAS cette allowlist — c'est :
#   1. `_PINNED_REGISTRY_COMMIT` (SHA figé, ligne ~32) : le contenu servi ne peut pas changer
#      sous nos pieds entre deux déploiements du bridge sans qu'on avance nous-mêmes le SHA ;
#   2. la revue humaine du diff du registre distant AVANT de faire avancer ce SHA (déjà en
#      place, cf. commentaire ci-dessus `_PINNED_REGISTRY_COMMIT`).
# L'allowlist + le filtre de métacaractères shell (`_SHELL_METACHAR_RE`) ne défendent que contre
# une classe étroite (commande hors liste, évasion shell) — pas contre un manifest malveillant
# qui reste dans les clous "node/python/docker" avec des arguments d'apparence légitime. Ne pas
# sur-vendre cette protection dans un futur audit ou une future doc utilisateur : elle réduit le
# risque, elle ne l'élimine pas. En complément (mesure proportionnée, PAS un sandboxing maison) :
# `_detect_inline_exec_flags` ci-dessous rend visible, sans jamais bloquer, les flags d'exécution
# inline les plus évidents ; et toute installation stdio est journalisée en WARNING (command+args
# complets) pour que la revue humaine ait une trace d'audit après coup.
_ALLOWED_STDIO_COMMANDS = frozenset(
    {"npx", "uvx", "node", "python", "python3", "docker", "deno", "bunx", "uv", "pnpm"}
)

# Métacaractères shell : n'ont rien à faire dans un ``command``/``args`` de manifest MCP.
# ``subprocess`` est invoqué en liste d'arguments (jamais ``shell=True``) donc ils ne sont pas
# interprétés aujourd'hui, mais on les bloque quand même à la source (défense en profondeur —
# un futur appelant qui construirait une commande shell à partir de ces champs ne doit pas
# hériter d'une charge utile déjà présente dans un manifest distant compromis).
_SHELL_METACHAR_RE = re.compile(r"[;&|$`<>\n\r]")


def _is_safe_stdio_command(command: object) -> bool:
    """``command`` n'est accepté que s'il désigne un lanceur attendu, en toutes lettres.

    Refuse : valeur non textuelle, chemin absolu ou relatif (``/usr/bin/sh``, ``../x``),
    métacaractère shell, casse non minuscule (évite les variantes trompeuses), et surtout
    tout ce qui n'est pas dans ``_ALLOWED_STDIO_COMMANDS``.
    """
    if not isinstance(command, str):
        return False
    command = command.strip()
    if not command or command != command.lower():
        return False
    if _SHELL_METACHAR_RE.search(command):
        return False
    if "/" in command or "\\" in command or ".." in command:
        return False
    return command in _ALLOWED_STDIO_COMMANDS


def _is_safe_stdio_args(args: object) -> bool:
    """``args`` ne doit contenir aucun métacaractère shell (défense en profondeur, cf. ci-dessus)."""
    if not isinstance(args, list):
        return False
    return not any(_SHELL_METACHAR_RE.search(str(a)) for a in args)


# Flags d'exécution inline évidents pour les interpréteurs de l'allowlist (node/python/deno...).
# Détection best-effort, PAS une liste exhaustive (ex. ne couvre pas `python -m ...` ni les
# variantes longues au-delà de celles listées) : le but n'est pas de bloquer (un serveur MCP
# légitime peut avoir besoin de `-e`/`-c` dans son lancement), seulement de rendre le risque
# VISIBLE dans les logs/retour, en complément honnête de la limite documentée ci-dessus.
_INLINE_EXEC_FLAGS = frozenset({"-e", "-c", "-p", "--eval"})


def _detect_inline_exec_flags(args: object) -> list[str]:
    """Repère, sans bloquer, les flags d'exécution de code inline présents dans ``args``.

    Renvoie la liste (ordonnée, avec doublons) des flags détectés parmi ``_INLINE_EXEC_FLAGS``.
    Liste vide si ``args`` n'est pas une liste ou ne contient aucun flag suspect.
    """
    if not isinstance(args, list):
        return []
    return [str(a) for a in args if str(a) in _INLINE_EXEC_FLAGS]


# Dédoublonnage de la journalisation d'audit (par process) : un même connecteur stdio, revu à
# chaque rafraîchissement du cache (30 min), ne doit pas noyer les logs — on journalise une fois
# par signature (id, command, args) tant que le manifest ne change pas. `clear_cache()` réinitialise
# aussi cet état (tests, ou volonté explicite de tout re-journaliser après un rafraîchissement forcé).
_logged_stdio_signatures: set[tuple[str, str, tuple[str, ...]]] = set()


def _log_stdio_registry_install(entry_id: str, command: str, args: list[str]) -> None:
    """Journalise en WARNING, pour audit, la commande+arguments complets d'un MCP stdio du
    registre distant classé installable (finding HAUTE nuancée, cf. limite documentée plus haut).

    Le niveau WARNING (pas INFO) est délibéré : ce n'est jamais anodin qu'un binaire arbitraire
    (même allowlisté) devienne installable depuis un registre non signé — un humain doit pouvoir
    retrouver cette trace en filtrant les logs sur la sévérité, sans avoir à activer un niveau de
    verbosité complet.
    """
    signature = (entry_id, command, tuple(args))
    with _lock:
        if signature in _logged_stdio_signatures:
            return
        _logged_stdio_signatures.add(signature)

    inline_flags = _detect_inline_exec_flags(args)
    if inline_flags:
        _logger.warning(
            "MCP stdio du registre distant avec flag(s) d'exécution inline %s (id=%r "
            "command=%r args=%r) — l'allowlist de commandes ne bloque pas ceci (node/python/"
            "docker restent Turing-complets par construction), revue humaine recommandée avant "
            "d'activer ce connecteur",
            inline_flags,
            entry_id,
            command,
            args,
        )
    else:
        _logger.warning(
            "MCP stdio du registre distant classé installable : id=%r command=%r args=%r "
            "(trace d'audit — cf. limite intrinsèque de l'allowlist documentée dans "
            "mcp_registry.py)",
            entry_id,
            command,
            args,
        )


def _install_kind(manifest: dict) -> str:
    """Classe le mode d'installation d'un MCP d'après son manifest.

    Un MCP ``stdio`` dont ``command``/``args`` ne passent pas l'allowlist (finding HAUTE #3)
    est classé ``unknown`` — donc jamais ``installable`` (cf. ``_enrich``), quel que soit le
    reste du manifest : on empêche une commande HORS LISTE (ou une évasion shell) d'atteindre
    l'UI d'install. Ceci NE GARANTIT PAS l'absence d'exécution de code pour une commande DANS
    la liste (``node``, ``python``/``python3``, ``docker``... restent Turing-complets) — voir
    la limite intrinsèque documentée au-dessus de ``_ALLOWED_STDIO_COMMANDS`` : la vraie
    frontière de confiance est le commit épinglé + la revue humaine, pas ce filtre.
    ``command`` absent (manifest incomplet) n'est pas rejeté ici — ``install_from_registry``
    le refuse déjà explicitement (« manifest stdio incomplet ») ; on ne valide l'allowlist que
    quand une commande est effectivement présente.
    """
    transport = str(manifest.get("transport") or "").lower()
    if transport in ("http", "sse"):
        return "local_app" if _is_localhost(manifest.get("url")) else "remote"
    if transport == "stdio":
        command = manifest.get("command")
        if command is not None and not _is_safe_stdio_command(command):
            return "unknown"
        if not _is_safe_stdio_args(manifest.get("args") or []):
            return "unknown"
        required = (manifest.get("configSchema") or {}).get("required") or []
        return "stdio_key" if required else "stdio_plain"
    return "unknown"


# Mots-clés (insensibles à la casse) qui trahissent un champ secret même en casse mixte —
# filet de sécurité quand le manifest ne déclare pas explicitement ``"secret": true/false``
# (finding HAUTE #2 : ``name.isupper()`` seul laissait passer ``apiToken`` en clair).
_SECRET_NAME_HINTS = ("key", "token", "secret", "password", "credential", "authorization")


def _looks_like_secret(name: str) -> bool:
    lname = name.lower()
    return any(hint in lname for hint in _SECRET_NAME_HINTS)


def _field_target(name: str, spec: dict) -> str:
    """Où injecter un champ de config dans la conf MCP, d'après le manifest.

    Ordre de décision :
    1. ``array``                              → étendre ``args`` (ex. ``allowedDirectories``).
    2. ``spec["secret"]`` déclaré explicitement (bool) → priorité absolue (source de vérité
       structurelle du manifest, pas une heuristique).
    3. nom EN MAJUSCULES **ou** contenant un mot-clé de secret, quelle que soit la casse
       (ex. ``apiToken``, ``Authorization``, ``clientSecret``) → variable d'environnement.
       Défaut sûr : en cas de doute sur un nom de secret, on protège plutôt que d'exposer.
    4. sinon (chemin/url)                      → valeur ajoutée à ``args`` (ex. ``db_path``).
    """
    if str(spec.get("type") or "string") == "array":
        return "args_list"
    explicit_secret = spec.get("secret")
    if isinstance(explicit_secret, bool):
        return "env" if explicit_secret else "arg_value"
    if name.isupper() or _looks_like_secret(name):
        return "env"
    return "arg_value"


def _config_fields(manifest: dict) -> list[dict]:
    """Champs à demander à l'utilisateur pour un MCP stdio (depuis ``configSchema``)."""
    schema = manifest.get("configSchema") or {}
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields = []
    for name, spec in props.items():
        spec = spec if isinstance(spec, dict) else {}
        target = _field_target(name, spec)
        fields.append(
            {
                "key": name,
                "label": str(spec.get("description") or name),
                "type": str(spec.get("type") or "string"),
                # secret = clé/token saisi en MAJUSCULES → masqué et stocké dans .env.
                "secret": target == "env",
                "required": name in required,
                "target": target,  # interne (env|args_list|arg_value) — non exposé au front
            }
        )
    return fields


def _fetch_manifest(path: str) -> dict:
    """Récupère le manifest d'un MCP. {} en cas d'erreur (entrée alors non installable)."""
    path = (path or "").strip()
    if not path:
        return {}
    try:
        data = _get_json_retry(_RAW_BASE + path + "/manifest.json")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _enrich(entry: dict) -> dict:
    """Ajoute à une entrée d'index les infos d'installation tirées de son manifest."""
    manifest = _fetch_manifest(entry.get("_path", ""))
    kind = _install_kind(manifest)
    transport = str(manifest.get("transport") or "http").lower()
    auth = "oauth" if kind == "remote" else ("key" if kind == "stdio_key" else "none")
    # Tout MCP du registre dont on sait l'installer (remote, app locale, ou stdio) est installable.
    installable = kind in ("remote", "local_app", "stdio_key", "stdio_plain")
    command = manifest.get("command")
    args = [str(a) for a in (manifest.get("args") or [])]
    inline_exec_flags: list[str] = []
    if kind in ("stdio_key", "stdio_plain"):
        inline_exec_flags = _detect_inline_exec_flags(args)
        _log_stdio_registry_install(entry.get("id", ""), str(command or ""), args)
    return {
        **{k: v for k, v in entry.items() if k != "_path"},
        "transport": transport,
        "url": manifest.get("url"),
        "auth": auth,
        "install_kind": kind,
        "config_fields": _config_fields(manifest),
        # Détails d'install (internes, consommés par install_from_registry, pas exposés en API).
        "command": command,
        "args": args,
        # Visibilité (non bloquante) des flags d'exécution inline évidents (cf. limite de
        # l'allowlist documentée plus haut) — [] si aucun ou si le MCP n'est pas stdio.
        "inline_exec_flags": inline_exec_flags,
        "installable": installable,
        "install_method": "registry" if installable else "",
    }


def _disk_cache_path() -> Path:
    from . import hermes_adapter

    return hermes_adapter.HERMES_HOME / ".agentos-mcp-catalog-cache.json"


def _load_disk_cache() -> list[dict] | None:
    try:
        data = json.loads(_disk_cache_path().read_text())
        entries = data.get("entries")
        return entries if isinstance(entries, list) and entries else None
    except Exception:
        return None


def _save_disk_cache(entries: list[dict]) -> None:
    try:
        _disk_cache_path().write_text(json.dumps({"entries": entries}))
    except Exception:  # noqa: BLE001 — cache non critique, ne jamais casser le rafraîchissement
        _logger.debug("écriture du cache disque MCP échouée (non bloquant)", exc_info=True)


def _fetch_fresh() -> list[dict]:
    """Récupère index + manifests (bloquant). Lève si l'index est injoignable."""
    index = _parse_index(_get_json_retry(_INDEX_URL))
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MANIFEST_WORKERS) as pool:
        return list(pool.map(_enrich, index))


def _refresh_worker() -> None:
    global _cache, _refreshing
    try:
        entries = _fetch_fresh()
        with _lock:
            _cache = (time.monotonic(), entries)
        _save_disk_cache(entries)
    except Exception:  # noqa: BLE001 — rafraîchissement best-effort, jamais bloquant
        _logger.warning("rafraîchissement du catalogue MCP échoué (le cache existant reste servi)", exc_info=True)
    finally:
        with _lock:
            _refreshing = False


def _trigger_refresh() -> None:
    """Lance un rafraîchissement en arrière-plan (un seul à la fois)."""
    global _refreshing
    with _lock:
        if _refreshing:
            return
        _refreshing = True
    threading.Thread(target=_refresh_worker, daemon=True).start()


def fetch_registry_mcps(*, force: bool = False) -> list[dict]:
    """Liste enrichie des MCP du registre (index + manifests, avec cache).

    Stale-while-revalidate : on renvoie TOUJOURS le cache disponible immédiatement (mémoire,
    sinon disque) pour ne jamais faire attendre l'utilisateur, et on rafraîchit en arrière-plan
    s'il est périmé. Seul le tout premier appel sans aucun cache est bloquant.
    """
    global _cache
    now = time.monotonic()

    # 1) Cache mémoire frais → retour direct.
    if not force and _cache is not None and (now - _cache[0]) < _CACHE_TTL_S:
        return _cache[1]

    # 2) Pas de cache mémoire : on tente le disque (instantané après un redémarrage), marqué
    #    périmé pour déclencher un rafraîchissement de fond.
    if _cache is None:
        disk = _load_disk_cache()
        if disk is not None:
            _cache = (now - _CACHE_TTL_S - 1, disk)

    # 3) On a un cache (même périmé) → on le renvoie tout de suite + refresh en arrière-plan.
    if _cache is not None and not force:
        _trigger_refresh()
        return _cache[1]

    # 4) Aucun cache (tout premier démarrage, avant le cache disque). Single-flight : on
    #    (re)lance un refresh de fond et on l'attend brièvement, plutôt que de multiplier les
    #    fetches concurrents. Renvoie [] si le registre est lent/injoignable (cas rare et bref).
    if not force:
        _trigger_refresh()
        for _ in range(75):  # ~15 s max
            time.sleep(0.2)
            with _lock:
                cached, busy = _cache, _refreshing
            if cached is not None:
                return cached[1]
            if not busy:
                break
        return []

    # force : fetch bloquant explicite (rafraîchissement manuel).
    try:
        entries = _fetch_fresh()
    except Exception:
        return _cache[1] if _cache is not None else []
    with _lock:
        _cache = (time.monotonic(), entries)
    _save_disk_cache(entries)
    return entries


def prewarm() -> None:
    """Préchauffe le cache au démarrage du bridge (charge le disque, rafraîchit en fond)."""
    global _cache
    if _cache is None:
        disk = _load_disk_cache()
        if disk is not None:
            _cache = (time.monotonic() - _CACHE_TTL_S - 1, disk)
    _trigger_refresh()


def find(entry_id: str) -> dict | None:
    """Renvoie l'entrée enrichie d'un MCP du registre par son id (ou None)."""
    entry_id = (entry_id or "").strip().lower()
    for e in fetch_registry_mcps():
        if e["id"] == entry_id:
            return e
    return None


def clear_cache() -> None:
    """Vide le cache mémoire (tests, ou rafraîchissement forcé).

    Protégé par ``_lock`` comme toutes les autres écritures de ``_cache``/``_refreshing``
    du module (finding MOYENNE #4) — sinon un refresh de fond en cours peut se retrouver
    dans un état incohérent (deux fetches concurrents vers le registre distant).

    Vide aussi le dédoublonnage de la journalisation d'audit (``_logged_stdio_signatures``) :
    un rafraîchissement forcé doit pouvoir re-journaliser, pas rester silencieux parce qu'un
    précédent process avait déjà vu la même signature.
    """
    global _cache, _refreshing
    with _lock:
        _cache = None
        _refreshing = False
        _logged_stdio_signatures.clear()
