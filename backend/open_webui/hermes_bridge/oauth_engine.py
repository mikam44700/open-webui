"""Moteur OAuth centralisé « 1 clic » — Agent OS (feature 016).

Implémente le flow Authorization Code + PKCE S256 pour tous les fournisseurs du
registre ``oauth_providers.py``. Les credentials centralisés (client_id / client_secret)
sont lus depuis l'environnement du processus bridge ; ils ne sont JAMAIS transmis au
front ni inscrits dans les logs.

Flow complet :
1. ``build_auth_url``  — génère l'URL d'autorisation + persiste l'état PKCE pending.
2. ``exchange_code``   — vérifie le state anti-CSRF, échange le code contre un token,
                         stocke le token, supprime le pending.
3. ``token_status``    — "connected" si le fichier token existe, sinon "not_connected".
4. ``disconnect``      — supprime le fichier token et le pending.

Sécurité :
- PKCE S256 : ``code_verifier`` aléatoire 128 octets → ``code_challenge`` = SHA-256 base64url.
- ``state`` anti-CSRF : 32 octets aléatoires, persisté côté serveur, vérifié au retour.
- Fichiers sensibles créés en 0600 (token) / dossier pending 0700.
- Aucun secret ni valeur de token n'est loggué ou renvoyé au front.

Cf. specs/016-oauth-un-clic/spec.md et oauth_providers.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from base64 import urlsafe_b64encode
from pathlib import Path

import httpx

from . import hermes_adapter
from .hermes_adapter import HERMES_HOME, HermesUnavailable
from .oauth_providers import OAuthProviderDef, by_id


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


def _pending_dir() -> Path:
    """Dossier de stockage des états pending PKCE (HERMES_HOME/oauth-pending/)."""
    return HERMES_HOME / "oauth-pending"


def _pending_path(provider_id: str, state: str) -> Path:
    """Chemin du fichier pending pour un flow OAuth donné (provider + state).

    Chaque flow (un appel à ``build_auth_url``) a son propre fichier, distingué par un
    hash du ``state`` anti-CSRF généré pour ce flow précis. Avant ce fix, la clé était
    ``{provider_id}.json`` seule : un second flow concurrent pour le même fournisseur
    (ex. le dirigeant reclique « Se connecter » dans un nouvel onglet sans avoir fini le
    premier) écrasait silencieusement le pending du premier, qui échouait ensuite avec
    un state qui ne correspondait plus à rien (cf. finding audit 05 #2). Le ``state``
    est haché (SHA-256) plutôt qu'utilisé tel quel dans le nom de fichier : il redevient
    une entrée utilisateur au retour du fournisseur (``exchange_code`` le reçoit en
    paramètre de requête), et un hash hexadécimal élimine tout risque d'injection de
    caractères de chemin.
    """
    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return _pending_dir() / f"{provider_id}-{digest}.json"


_PENDING_FILENAME_RE_SUFFIX = r"-[0-9a-f]{64}\.json$"


def _clear_pending_flows(provider_id: str) -> None:
    """Supprime tous les flows OAuth pending d'un fournisseur, quel que soit l'onglet
    qui les a créés.

    Contrepartie de la clé composite ``provider_id`` + ``state`` (cf. ``_pending_path``) :
    ``disconnect`` ne connaît que le ``provider_id``, jamais un ``state`` précis — il doit
    donc balayer tous les fichiers pending de ce fournisseur. Le motif exige un suffixe
    hex de 64 caractères pour ne matcher QUE les fichiers de ce provider_id exact (pas un
    fournisseur dont l'id serait un préfixe du nôtre, ex. un futur ``google`` face à
    ``google-workspace``).
    """
    pending_dir = _pending_dir()
    if not pending_dir.exists():
        return
    pattern = re.compile(rf"^{re.escape(provider_id)}{_PENDING_FILENAME_RE_SUFFIX}")
    for entry in pending_dir.iterdir():
        if entry.is_file() and pattern.match(entry.name):
            entry.unlink(missing_ok=True)


def _token_path(provider: OAuthProviderDef) -> Path:
    """Chemin du fichier token (présence = connecté)."""
    return HERMES_HOME / provider.token_file


def _resolve_provider(provider_id: str) -> OAuthProviderDef:
    """Retourne la définition du fournisseur ou lève ``HermesUnavailable``."""
    provider = by_id(provider_id)
    if provider is None:
        raise HermesUnavailable(f"fournisseur OAuth inconnu : {provider_id!r}")
    return provider


def _read_client_id(provider: OAuthProviderDef) -> str:
    """Lit le client_id centralisé depuis l'environnement.

    Lève ``HermesUnavailable`` si la variable n'est pas définie — le serveur n'est
    pas encore provisionné avec les credentials de l'app centralisée.
    """
    value = os.environ.get(provider.client_id_env, "")
    if not value:
        raise HermesUnavailable(
            f"credentials centralisés absents : variable {provider.client_id_env!r} non définie"
        )
    return value


def _read_client_secret(provider: OAuthProviderDef) -> str:
    """Lit le client_secret centralisé depuis l'environnement.

    Lève ``HermesUnavailable`` si absent. Jamais loggué.
    """
    value = os.environ.get(provider.client_secret_env, "")
    if not value:
        raise HermesUnavailable(
            f"credentials centralisés absents : variable {provider.client_secret_env!r} non définie"
        )
    return value


def _pkce_pair() -> tuple[str, str]:
    """Génère un couple (code_verifier, code_challenge) PKCE S256.

    - ``code_verifier``  : 128 octets aléatoires encodés base64url (RFC 7636).
    - ``code_challenge`` : SHA-256(code_verifier) encodé base64url sans rembourrage.
    """
    raw = secrets.token_bytes(96)  # 96 octets -> 128 caractères base64url
    code_verifier = urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def _format_token_for_storage(
    provider: OAuthProviderDef,
    token_data: dict,
    client_id: str,
    client_secret: str,
    previous_refresh_token: str | None = None,
) -> dict:
    """Transforme la réponse brute du fournisseur vers le format de stockage attendu.

    Paramètres
    ----------
    provider:
        Définition du fournisseur (contient ``token_format`` et ``token_url``).
    token_data:
        Réponse brute JSON du fournisseur (résultat de l'échange de code ou du refresh).
    client_id:
        ``client_id`` centralisé (jamais loggué).
    client_secret:
        ``client_secret`` centralisé (jamais loggué).
    previous_refresh_token:
        ``refresh_token`` issu d'un échange précédent, utilisé pour préserver le token
        si la réponse de renouvellement n'en renvoie pas de nouveau (cas courant chez
        Google lors d'un refresh).

    Retour
    ------
    Dict prêt à être sérialisé en JSON et écrit dans ``token_file``.

    - ``"raw"`` (défaut) : ``token_data`` retourné inchangé.
    - ``"google_authorized_user"`` : format ``authorized_user`` strict requis par
      ``google.oauth2.credentials.Credentials.from_authorized_user_file()``.
    """
    if provider.token_format != "google_authorized_user":
        # Comportement inchangé pour tous les fournisseurs sans format spécial.
        return token_data

    # Résolution du refresh_token : préférer celui contenu dans la réponse courante ;
    # en cas d'absence (refresh sans rotation), utiliser l'ancien.
    refresh = token_data.get("refresh_token") or previous_refresh_token or ""

    # Conversion des scopes : Google renvoie une chaîne espace-séparée ; google-auth
    # attend une liste de chaînes.
    scope_str: str = token_data.get("scope", "")
    scopes_list: list[str] = [s for s in scope_str.split() if s]

    return {
        "type": "authorized_user",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh,
        "token": token_data.get("access_token", ""),
        "token_uri": provider.token_url,
        "scopes": scopes_list,
    }


def _write_secure(path: Path, data: str) -> None:
    """Écrit ``data`` dans ``path`` avec les permissions 0600 (lecture propriétaire seul)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Sécurisation du dossier parent si c'est le dossier pending
    if path.parent.name == "oauth-pending":
        os.chmod(path.parent, stat.S_IRWXU)
    # Création atomique avec les bonnes permissions dès le départ
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(path), flags, 0o600)
    try:
        os.write(fd, data.encode("utf-8"))
    finally:
        os.close(fd)


def _write_client_secret_file(
    provider: OAuthProviderDef, client_id: str, client_secret: str
) -> None:
    """Écrit le fichier ``client_secret`` (format Google Cloud, clé ``web``) attendu par
    certaines skills Hermes en plus du token, dans ``HERMES_HOME / provider.client_secret_file``.

    No-op si le fournisseur ne déclare pas de ``client_secret_file`` (cas général). Reconstruit
    depuis les identifiants OAuth centralisés — mêmes valeurs que celles déjà stockées dans le
    token — en 0600. Aucune modification de la skill Hermes (cf. google-workspace)."""
    if not provider.client_secret_file:
        return
    payload = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": provider.auth_url,
            "token_uri": provider.token_url,
        }
    }
    _write_secure(
        HERMES_HOME / provider.client_secret_file,
        json.dumps(payload, ensure_ascii=False),
    )


def _post_token_request(
    provider: OAuthProviderDef,
    payload: dict[str, str],
    client_id: str,
    client_secret: str,
) -> dict | None:
    """POST commun d'échange/renouvellement de token, factorisé entre ``exchange_code``
    et ``refresh_token`` (mêmes en-têtes, même choix Basic-auth vs body, même POST,
    même gestion d'erreur — cf. finding audit dédup 2026-07).

    Ajoute l'authentification client à ``payload`` (mutation en place) : HTTP Basic
    (``provider.token_auth == "basic"``) ou credentials injectés dans le corps du POST
    (défaut). Envoie la requête sur ``provider.token_url``.

    Retour
    ------
    Le dict JSON décodé de la réponse si le POST a réussi (statut 200 + JSON valide
    contenant un ``access_token`` non vide). ``None`` en cas d'erreur réseau, de statut
    non-200, de JSON invalide, ou de réponse 200 sans ``access_token`` exploitable —
    un fournisseur (ou un proxy intermédiaire) qui répond 200 avec un corps d'erreur ne
    doit jamais être traité comme un succès (cf. finding audit 05 #4). Aucun secret
    n'est loggué ; aucune exception non gérée n'est propagée.
    """
    # En-têtes communs : Accept JSON (GitHub renvoie form-urlencoded sans cet en-tête)
    headers: dict[str, str] = {"Accept": "application/json"}

    # Authentification du client : HTTP Basic ou credentials dans le corps du POST
    auth_param = None
    if provider.token_auth == "basic":
        # HTTP Basic : client_id:client_secret encodé en Base64 (ex. Notion)
        auth_param = (client_id, client_secret)
    else:
        # Défaut "body" : credentials dans le corps du POST (Microsoft, GitHub, Airtable)
        payload[provider.client_id_param] = client_id
        payload["client_secret"] = client_secret

    try:
        resp = httpx.post(
            provider.token_url,
            data=payload,
            headers=headers,
            auth=auth_param,
            timeout=30.0,
        )
    except httpx.RequestError:
        return None

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    # Un statut 200 ne garantit pas un succès exploitable : un fournisseur/proxy peut
    # répondre 200 avec un corps d'erreur (ex. {"error": "..."}). Sans access_token,
    # persister ce contenu comme s'il s'agissait d'un token valide casserait
    # silencieusement le prochain appel API réel (cf. finding audit 05 #4).
    if not isinstance(data, dict) or not data.get("access_token"):
        return None

    return data


def _exchange_long_lived(
    provider: OAuthProviderDef,
    token_data: dict,
    client_id: str,
    client_secret: str,
) -> dict:
    """Échange un token court Meta contre un token longue durée (~60 j).

    Spécifique Meta (``grant_type=fb_exchange_token``, GET sur ``token_url``). En cas
    d'échec (réseau, réponse invalide, pas d'``access_token``), retourne ``token_data``
    inchangé — la connexion reste fonctionnelle à court terme. Aucun secret n'est loggué.
    """
    short_token = token_data.get("access_token", "")
    if not short_token:
        return token_data
    try:
        resp = httpx.get(
            provider.token_url,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "fb_exchange_token": short_token,
            },
            headers={"Accept": "application/json"},
            timeout=30.0,
        )
    except httpx.RequestError:
        return token_data
    if resp.status_code != 200:
        return token_data
    try:
        long_data = resp.json()
    except ValueError:
        return token_data
    if long_data.get("access_token"):
        return long_data
    return token_data


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------


def build_auth_url(provider_id: str, redirect_uri: str) -> str:
    """Génère l'URL d'autorisation OAuth pour le fournisseur donné.

    Paramètres
    ----------
    provider_id:
        Identifiant du fournisseur (ex. "microsoft-365").
    redirect_uri:
        URI de redirection enregistrée (doit correspondre à celle configurée chez le
        fournisseur — ex. ``http://localhost:3000/integrations/oauth/callback``).

    Retour
    ------
    URL complète à ouvrir dans le navigateur du client.

    Erreurs
    -------
    ``HermesUnavailable`` :
        - Fournisseur inconnu dans le registre.
        - Variable d'environnement ``client_id_env`` absente (serveur non provisionné).
    """
    provider = _resolve_provider(provider_id)
    client_id = _read_client_id(provider)

    # Génération du state anti-CSRF et des paramètres PKCE
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _pkce_pair()

    # Persistance de l'état pending (state + code_verifier + redirect_uri)
    pending_payload = json.dumps(
        {
            "state": state,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        },
        ensure_ascii=False,
    )
    _write_secure(_pending_path(provider_id, state), pending_payload)

    # Construction des paramètres de la requête d'autorisation
    scope = " ".join(provider.scopes)
    params: dict[str, str] = {
        "response_type": "code",
        # Nom du paramètre du client : "client_id" par défaut, "client_key" pour TikTok.
        provider.client_id_param: client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }
    if provider.use_pkce:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    # Paramètres supplémentaires spécifiques au fournisseur (ex. prompt=consent pour
    # Microsoft, token_access_type=offline pour Dropbox). Définis dans OAuthProviderDef
    # via extra_auth_params — remplace les anciens hacks en dur par fournisseur.
    for key, value in provider.extra_auth_params:
        params[key] = value

    # Construction de l'URL (urllib plutôt qu'une dépendance supplémentaire)
    from urllib.parse import urlencode

    query = urlencode(params)
    return f"{provider.auth_url}?{query}"


def exchange_code(provider_id: str, code: str, state: str) -> bool:
    """Échange le code d'autorisation contre un token d'accès.

    Vérifie le ``state`` anti-CSRF, POST sur le ``token_url`` du fournisseur,
    stocke la réponse JSON dans ``HERMES_HOME / token_file`` (0600), supprime
    le fichier pending.

    Retour
    ------
    ``True`` si l'échange a réussi et le token est stocké, ``False`` sinon.
    Aucune exception non gérée n'est propagée (erreurs réseau, réponses d'erreur).
    Aucun secret ni contenu de token n'est inscrit dans les logs.
    """
    provider = _resolve_provider(provider_id)
    pending_file = _pending_path(provider_id, state)

    # Lecture et vérification de l'état pending. Le fichier est retrouvé par le state
    # reçu : chaque flow a le sien, un flow concurrent (même fournisseur, onglet
    # différent) ne peut plus l'écraser (cf. finding audit 05 #2).
    if not pending_file.exists():
        return False

    try:
        pending = json.loads(pending_file.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False

    # Vérification anti-CSRF : le state doit correspondre exactement
    if not secrets.compare_digest(pending.get("state", ""), state):
        return False

    code_verifier: str = pending.get("code_verifier", "")
    redirect_uri: str = pending.get("redirect_uri", "")

    # Lecture des credentials centralisés (jamais loggués)
    try:
        client_id = _read_client_id(provider)
        client_secret = _read_client_secret(provider)
    except HermesUnavailable:
        return False

    # Échange code -> token
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    if provider.use_pkce and code_verifier:
        payload["code_verifier"] = code_verifier

    # POST commun (en-têtes, Basic vs body, requête, gestion d'erreur) — factorisé
    # avec refresh_token dans _post_token_request (finding audit dédup 2026-07).
    token_data = _post_token_request(provider, payload, client_id, client_secret)
    if token_data is None:
        return False

    # Meta : échange du token court contre un token longue durée (~60 j) avant stockage.
    # No-op pour tous les autres fournisseurs (long_lived_exchange=False).
    if provider.long_lived_exchange:
        token_data = _exchange_long_lived(provider, token_data, client_id, client_secret)

    # Transformation vers le format de stockage attendu (ex. "authorized_user" pour Google).
    # Pour tous les autres fournisseurs (token_format="raw"), retourne token_data inchangé.
    formatted = _format_token_for_storage(provider, token_data, client_id, client_secret)

    # Stockage du token (présence du fichier = connecté)
    token_json = json.dumps(formatted, ensure_ascii=False)
    _write_secure(_token_path(provider), token_json)

    # Fichier client_secret additionnel exigé par certaines skills (ex. google-workspace).
    _write_client_secret_file(provider, client_id, client_secret)

    # Suppression du pending une fois le token sécurisé
    pending_file.unlink(missing_ok=True)

    # Propagation vers ~/.hermes/.env si la skill Hermes lit la clé depuis cet emplacement.
    # L'access_token OAuth de ces fournisseurs est directement utilisable comme Bearer.
    # La valeur n'est jamais journalisée.
    if provider.env_key:
        access_token = token_data.get("access_token", "")
        if access_token:
            hermes_adapter._set_env_value(provider.env_key, access_token)

    return True


def token_status(provider_id: str) -> str:
    """Retourne l'état de connexion OAuth pour le fournisseur.

    Retour
    ------
    ``"connected"``     si le fichier token existe (preuve réelle de connexion).
    ``"not_connected"`` sinon.

    Jamais ``"connected"`` sans preuve réelle (cf. honnetete-libelles-etat-ui).
    """
    provider = _resolve_provider(provider_id)
    if _token_path(provider).exists():
        return "connected"
    return "not_connected"


def _revoke_remote_token(provider: OAuthProviderDef) -> None:
    """Révoque le token chez le fournisseur (best-effort) si ``revoke_url`` est défini.

    Lit le token local, en extrait le ``refresh_token`` (à défaut l'access_token) et le
    POST sur ``provider.revoke_url``. Toute erreur (fichier illisible, réseau, statut
    non-200) est silencieusement ignorée : la déconnexion locale doit toujours réussir.
    Aucun secret n'est journalisé.
    """
    if not provider.revoke_url:
        return
    token_file = _token_path(provider)
    if not token_file.exists():
        return
    try:
        token_data = json.loads(token_file.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    # refresh_token en priorité : le révoquer invalide tout le grant (access inclus).
    token = (
        token_data.get("refresh_token")
        or token_data.get("token")
        or token_data.get("access_token")
    )
    if not token:
        return

    try:
        httpx.post(
            provider.revoke_url,
            data={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
    except httpx.RequestError:
        return  # best-effort : la déconnexion locale prime sur la révocation réseau


def disconnect(provider_id: str) -> None:
    """Déconnecte le fournisseur OAuth : révoque puis supprime le token local.

    Si le fournisseur définit un ``revoke_url``, le token est d'abord révoqué chez le
    fournisseur (best-effort, cf. ``_revoke_remote_token``) pour que « Déconnecter » ne
    mente pas (honnetete-libelles-etat-ui). Puis le fichier token et l'éventuel pending
    sont supprimés. N'échoue pas si les fichiers sont déjà absents, ni si la révocation
    réseau échoue.
    """
    provider = _resolve_provider(provider_id)
    _revoke_remote_token(provider)
    _token_path(provider).unlink(missing_ok=True)
    _clear_pending_flows(provider_id)


def refresh_token(provider_id: str) -> bool:
    """Renouvelle le token d'accès via le ``refresh_token`` stocké.

    Retour
    ------
    ``True`` si le renouvellement a réussi et le token est mis à jour.
    ``False`` si le token n'existe pas, ne contient pas de refresh_token, ou si
    la requête échoue. Aucun secret n'est loggué.
    """
    provider = _resolve_provider(provider_id)
    token_file = _token_path(provider)

    if not token_file.exists():
        return False

    try:
        token_data = json.loads(token_file.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False

    refresh = token_data.get("refresh_token")
    if not refresh:
        return False

    try:
        client_id = _read_client_id(provider)
        client_secret = _read_client_secret(provider)
    except HermesUnavailable:
        return False

    payload: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    }

    # POST commun (en-têtes, Basic vs body, requête, gestion d'erreur) — factorisé
    # avec exchange_code dans _post_token_request (finding audit dédup 2026-07).
    new_token = _post_token_request(provider, payload, client_id, client_secret)
    if new_token is None:
        return False

    # Transformation vers le format de stockage attendu (ex. "authorized_user" pour Google).
    # Le refresh_token original est transmis comme fallback : si la réponse de renouvellement
    # ne contient pas de nouveau refresh_token (comportement courant chez Google), il est
    # réinjecté dans le format final pour ne pas le perdre.
    formatted = _format_token_for_storage(
        provider, new_token, client_id, client_secret, previous_refresh_token=refresh
    )

    # Pour les fournisseurs "raw" (comportement historique) : si le fournisseur n'a pas
    # renvoyé de refresh_token, on le préserve dans la réponse brute.
    if provider.token_format == "raw" and "refresh_token" not in new_token and refresh:
        formatted = {**formatted, "refresh_token": refresh}

    token_json = json.dumps(formatted, ensure_ascii=False)
    _write_secure(token_file, token_json)

    # Recrée aussi le fichier client_secret si le fournisseur l'exige (idempotent, robuste
    # au cas où il aurait été supprimé) — cf. google-workspace.
    _write_client_secret_file(provider, client_id, client_secret)

    # Propagation vers ~/.hermes/.env après renouvellement du token.
    # La valeur n'est jamais journalisée.
    if provider.env_key:
        new_access = new_token.get("access_token", "")
        if new_access:
            hermes_adapter._set_env_value(provider.env_key, new_access)

    return True
