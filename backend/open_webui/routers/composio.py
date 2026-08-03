"""Router Composio — LunarIA V2.

Composio tient un catalogue d'applications deja authentifiables (Gmail, Drive,
agenda, CRM) et gere lui-meme l'OAuth de chaque utilisateur final. On s'en sert
pour brancher ce que le moteur ne couvre pas : son propre catalogue MCP ne
compte que six serveurs, tous orientes developpement.

Ce router est un intermediaire, sur le meme modele que celui de Hermes :

  1. La cle Composio reste cote serveur. Le navigateur ne la recoit jamais, meme
     masquee, et ne joint jamais `backend.composio.dev` directement — la regle
     de l'URL unique vaut ici comme ailleurs.
  2. Tout est reserve a l'administrateur (`get_admin_user`).

Chaque client a sa propre cle : un projet Composio par client, donc une cle par
installation. Une fuite sur un serveur ne touche que ce client-la, et la
consommation se lit par projet.
"""

import asyncio
import logging
import time
from typing import Any, Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

# API publique de Composio. Les comptes connectes vivent sur une version mineure
# plus recente que le reste du catalogue — les deux coexistent chez eux.
COMPOSIO_API = "https://backend.composio.dev/api/v3"
COMPOSIO_API_COMPTES = "https://backend.composio.dev/api/v3.1"

# Emplacement de la cle. Meme convention que le reste de LunarIA (`lunaria.*`),
# stockee en base par le backend : elle survit au redemarrage du conteneur et
# n'est jamais rendue au navigateur.
CLE_CONFIG = "lunaria.composio_api_key"

TIMEOUT = aiohttp.ClientTimeout(total=20)
# L'ouverture d'une session d'autorisation interroge le fournisseur amont.
TIMEOUT_LONG = aiohttp.ClientTimeout(total=45)


async def _lire_cle() -> str:
    return str(await Config.get(CLE_CONFIG, "") or "")


def _entetes(cle: str) -> dict[str, str]:
    return {"x-api-key": cle, "Content-Type": "application/json"}


async def _appeler(
    chemin: str,
    cle: str,
    methode: str = "GET",
    corps: Optional[dict] = None,
    base: str = COMPOSIO_API,
    timeout: aiohttp.ClientTimeout = TIMEOUT,
) -> Any:
    """Relaie un appel vers Composio et rend sa reponse telle quelle.

    Les erreurs amont sont traduites en messages lisibles : l'ecran Integrations
    n'a pas a afficher une trace technique au client.

    Deux nouvelles tentatives sur les pannes passageres — DNS qui hoquette,
    coupure d'une seconde, 502 amont. Sans elles, un seul rate vidait l'ecran du
    client et lui laissait croire que ses applications s'etaient deconnectees.
    Une lecture qui echoue trois fois de suite est une vraie panne, et elle est
    alors annoncee comme telle.

    Seules les lectures sont retentees. Rejouer un POST creerait un second
    compte connecte ou une seconde configuration d'authentification.
    """
    url = f"{base}{chemin}"
    rejouable = methode.upper() in {"GET", "HEAD"}
    tentatives = 3 if rejouable else 1
    dernier: Optional[Exception] = None

    for tentative in range(tentatives):
        if tentative:
            await asyncio.sleep(0.6 * tentative)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    methode, url, headers=_entetes(cle), json=corps
                ) as reponse:
                    # Un 5xx amont est passager aussi : on retente comme le reste.
                    if reponse.status >= 500 and tentative + 1 < tentatives:
                        log.warning(
                            f"Composio {reponse.status} sur {chemin}, "
                            f"tentative {tentative + 1}/{tentatives}"
                        )
                        continue
                    return await _lire(reponse, methode, chemin)
        except (aiohttp.ClientError, TimeoutError) as exc:
            dernier = exc
            log.warning(
                f"Composio injoignable sur {url} "
                f"(tentative {tentative + 1}/{tentatives}) : {exc}"
            )

    if isinstance(dernier, TimeoutError):
        raise HTTPException(
            status_code=504, detail="Composio met trop de temps a repondre."
        )
    raise HTTPException(
        status_code=503,
        detail="Composio ne repond pas. Reessayez dans un instant.",
    )


async def _lire(reponse: aiohttp.ClientResponse, methode: str, chemin: str) -> Any:
    if reponse.status == 401 or reponse.status == 403:
        raise HTTPException(
            status_code=401,
            detail="Cle Composio refusee. Verifiez la cle du projet de ce client.",
        )
    if reponse.status >= 400:
        log.warning(f"Composio {methode} {chemin} -> {reponse.status}")
        detail = None
        try:
            charge = await reponse.json(content_type=None)
            if isinstance(charge, dict):
                detail = charge.get("detail") or charge.get("message") or charge.get(
                    "error"
                )
                if isinstance(detail, dict):
                    detail = detail.get("message")
        except Exception:
            pass
        raise HTTPException(
            status_code=reponse.status,
            detail=detail or f"Composio a refuse la demande ({reponse.status}).",
        )
    texte = await reponse.text()
    if not texte:
        return None
    try:
        return await reponse.json(content_type=None)
    except Exception:
        return {"texte": texte}


async def _cle_ou_erreur() -> str:
    cle = await _lire_cle()
    if not cle:
        raise HTTPException(
            status_code=409,
            detail="Aucune cle Composio enregistree sur cette installation.",
        )
    return cle


def _liste(charge: Any) -> list[dict]:
    """Composio enveloppe ses listes differemment selon les routes."""
    if isinstance(charge, list):
        return [element for element in charge if isinstance(element, dict)]
    if isinstance(charge, dict):
        for champ in ("items", "data", "results"):
            valeur = charge.get(champ)
            if isinstance(valeur, list):
                return [element for element in valeur if isinstance(element, dict)]
    return []


# --------------------------------------------------------------------------
# La cle du client
# --------------------------------------------------------------------------


class CleComposio(BaseModel):
    value: str


@router.get("/status")
async def etat(user=Depends(get_admin_user)):
    """Une cle est-elle posee, et Composio l'accepte-t-il ?

    Trois etats distincts, jamais confondus : `absente` (rien de pose),
    `ok` (Composio repond), `injoignable` (la cle existe mais on n'a pas pu
    verifier). Une source muette n'est pas une panne — c'est la regle D27.
    """
    cle = await _lire_cle()
    if not cle:
        return {"cle": False, "etat": "absente", "detail": None}
    try:
        await _appeler("/toolkits", cle)
        return {"cle": True, "etat": "ok", "detail": None}
    except HTTPException as exc:
        if exc.status_code == 401:
            return {"cle": True, "etat": "refusee", "detail": exc.detail}
        return {"cle": True, "etat": "injoignable", "detail": exc.detail}


@router.post("/key/validate")
async def verifier_cle(corps: CleComposio, user=Depends(get_admin_user)):
    """Essaie la cle chez Composio sans rien enregistrer."""
    valeur = corps.value.strip()
    if not valeur:
        raise HTTPException(status_code=400, detail="Cle vide.")
    try:
        await _appeler("/toolkits", valeur)
        return {"valide": True, "motif": None}
    except HTTPException as exc:
        if exc.status_code == 401:
            return {"valide": False, "motif": exc.detail}
        raise


@router.put("/key")
async def enregistrer_cle(corps: CleComposio, user=Depends(get_admin_user)):
    """Enregistre la cle apres l'avoir essayee.

    On verifie avant d'ecrire : une cle fausse posee en silence donnerait un
    ecran qui se dit branche et une liste d'applications vide, sans explication.
    """
    valeur = corps.value.strip()
    if not valeur:
        raise HTTPException(status_code=400, detail="Cle vide.")
    await _appeler("/toolkits", valeur)
    await Config.upsert({CLE_CONFIG: valeur})
    return {"ok": True}


@router.delete("/key")
async def retirer_cle(user=Depends(get_admin_user)):
    """Retire la cle de cette installation.

    Les comptes deja connectes restent chez Composio : ils ne sont pas effaces
    ici, seulement plus joignables depuis cet ecran. C'est dit a l'ecran.
    """
    if not await _lire_cle():
        raise HTTPException(
            status_code=409, detail="Aucune cle Composio a retirer."
        )
    await Config.upsert({CLE_CONFIG: ""})
    return {"ok": True}


# --------------------------------------------------------------------------
# Le catalogue d'applications et les connexions du client
# --------------------------------------------------------------------------


def _presenter(app: dict) -> dict:
    """Ce qu'une carte a besoin de savoir sur une application.

    Composio decrit lui-meme chacune de ses entrees : une phrase, le nombre
    d'actions disponibles, ses categories, son site. On reprend ces champs tels
    quels plutot que d'ecrire mille fiches a la main — elles seraient fausses
    dans six mois, et les inventer serait pire.

    Ces textes sont en anglais. Les applications mises en vitrine ont, elles,
    une fiche redigee en francais (`lib/composio/fiches.ts`) qui passe devant.
    """
    meta = app.get("meta") if isinstance(app.get("meta"), dict) else {}
    categories = [
        f"{c.get('name') or ''}".strip()
        for c in (meta.get("categories") or [])
        if isinstance(c, dict) and c.get("name")
    ]
    return {
        "slug": f"{app.get('slug') or app.get('name') or ''}".lower(),
        "nom": app.get("name") or app.get("slug") or "",
        "logo": app.get("logo") or meta.get("logo"),
        "description": f"{meta.get('description') or ''}".strip() or None,
        "actions": meta.get("tools_count"),
        "categories": categories,
        "site": meta.get("app_url"),
        # `no_auth` : l'application n'a rien a autoriser. Le dire evite un bouton
        # « Connecter » qui ouvrirait une fenetre vide.
        "sans_compte": bool(app.get("no_auth")),
    }


# Le catalogue compte plus de mille entrees et ne bouge quasiment pas. Le garder
# en memoire evite un aller-retour a chaque ouverture de l'onglet, et surtout : il
# reste servi quand Composio devient injoignable. Sans lui, une coupure de trois
# secondes vidait la page du client.
_CACHE_APPLICATIONS: dict[str, Any] = {"quand": 0.0, "donnees": None}
DUREE_CACHE = 600.0


@router.get("/toolkits")
async def applications(user=Depends(get_admin_user)):
    """Les applications que ce projet Composio peut brancher.

    En cas de panne amont, le dernier catalogue connu est servi plutot qu'une
    page vide : le client ne perd pas ses applications parce que le reseau a
    hoquete. `frais` dit lequel des deux il regarde.
    """
    cle = await _cle_ou_erreur()
    age = time.monotonic() - float(_CACHE_APPLICATIONS["quand"])
    if _CACHE_APPLICATIONS["donnees"] is not None and age < DUREE_CACHE:
        return {"applications": _CACHE_APPLICATIONS["donnees"], "frais": True}

    try:
        charge = await _appeler("/toolkits", cle)
    except HTTPException:
        if _CACHE_APPLICATIONS["donnees"] is not None:
            log.warning("Composio injoignable : catalogue servi depuis le cache.")
            return {"applications": _CACHE_APPLICATIONS["donnees"], "frais": False}
        raise

    liste = [_presenter(app) for app in _liste(charge) if app.get("slug") or app.get("name")]
    _CACHE_APPLICATIONS["donnees"] = liste
    _CACHE_APPLICATIONS["quand"] = time.monotonic()
    return {"applications": liste, "frais": True}


@router.get("/connections")
async def connexions(user=Depends(get_admin_user)):
    """Ce que ce client a deja connecte.

    `user_id` cote Composio = l'identifiant du compte LunarIA. Chaque personne
    garde ainsi ses propres acces, meme sur une installation partagee.
    """
    cle = await _cle_ou_erreur()
    charge = await _appeler(
        f"/connected_accounts?user_ids={user.id}", cle, base=COMPOSIO_API_COMPTES
    )
    return {
        "connexions": [
            {
                "id": compte.get("id") or compte.get("nanoid") or "",
                "application": f"{compte.get('toolkit', {}).get('slug') or compte.get('toolkit_slug') or ''}".lower(),
                "etat": f"{compte.get('status') or ''}".upper(),
            }
            for compte in _liste(charge)
        ]
    }


class DemandeConnexion(BaseModel):
    toolkit: str
    callback_url: Optional[str] = None


@router.post("/connections")
async def connecter(corps: DemandeConnexion, user=Depends(get_admin_user)):
    """Ouvre une session d'autorisation pour une application.

    Composio a besoin d'une « auth config » par application. On reutilise celle
    du projet quand elle existe deja, sinon on en cree une sur son OAuth gere :
    sans cela, chaque client devrait creer une application OAuth chez Google,
    ce qui est exactement le travail qu'on cherche a lui epargner.
    """
    cle = await _cle_ou_erreur()
    toolkit = corps.toolkit.strip().lower()
    if not toolkit:
        raise HTTPException(status_code=400, detail="Application non precisee.")

    config_id = await _config_auth(toolkit, cle)
    charge = await _appeler(
        "/connected_accounts",
        cle,
        methode="POST",
        corps={
            "auth_config_id": config_id,
            "user_id": user.id,
            **({"callback_url": corps.callback_url} if corps.callback_url else {}),
        },
        base=COMPOSIO_API_COMPTES,
        timeout=TIMEOUT_LONG,
    )
    charge = charge if isinstance(charge, dict) else {}
    url = charge.get("redirect_url") or charge.get("redirectUrl")
    if not url:
        raise HTTPException(
            status_code=502,
            detail="Composio n'a pas renvoye d'adresse d'autorisation.",
        )
    return {
        "url": url,
        "id": charge.get("id") or charge.get("nanoid") or "",
        "expire_le": charge.get("expires_at"),
    }


async def _config_auth(toolkit: str, cle: str) -> str:
    """Identifiant de la configuration d'authentification d'une application."""
    existantes = _liste(await _appeler(f"/auth_configs?toolkit_slug={toolkit}", cle))
    for config in existantes:
        identifiant = config.get("id") or config.get("nanoid")
        if identifiant:
            return f"{identifiant}"

    creee = await _appeler(
        "/auth_configs",
        cle,
        methode="POST",
        corps={"toolkit": {"slug": toolkit}, "auth_config": {"type": "use_composio_managed_auth"}},
        timeout=TIMEOUT_LONG,
    )
    creee = creee if isinstance(creee, dict) else {}
    interne = creee.get("auth_config") if isinstance(creee.get("auth_config"), dict) else creee
    identifiant = interne.get("id") or interne.get("nanoid")
    if not identifiant:
        raise HTTPException(
            status_code=502,
            detail=f"Composio n'a pas pu preparer la connexion a {toolkit}.",
        )
    return f"{identifiant}"


@router.get("/connections/{connexion_id}")
async def suivre_connexion(connexion_id: str, user=Depends(get_admin_user)):
    """Ou en est une autorisation en cours."""
    cle = await _cle_ou_erreur()
    charge = await _appeler(
        f"/connected_accounts/{connexion_id}", cle, base=COMPOSIO_API_COMPTES
    )
    charge = charge if isinstance(charge, dict) else {}
    return {
        "id": connexion_id,
        "etat": f"{charge.get('status') or ''}".upper(),
        "application": f"{charge.get('toolkit', {}).get('slug') or charge.get('toolkit_slug') or ''}".lower(),
    }


@router.delete("/connections/{connexion_id}")
async def retirer_connexion(connexion_id: str, user=Depends(get_admin_user)):
    """Retire une application connectee. Rien ne part sans confirmation a l'ecran."""
    cle = await _cle_ou_erreur()
    await _appeler(
        f"/connected_accounts/{connexion_id}",
        cle,
        methode="DELETE",
        base=COMPOSIO_API_COMPTES,
    )
    return {"ok": True}


# --------------------------------------------------------------------------
# Brancher Composio sur le moteur
# --------------------------------------------------------------------------
#
# Connecter Gmail chez Composio ne suffit pas : encore faut-il que l'agent sache
# s'en servir. Cela passe par un serveur MCP distant, declare dans Hermes.
#
# Hermes refuse de le poser par sa route d'ajout : `POST /api/mcp/servers` ne
# sait ecrire qu'un en-tete `Authorization: Bearer`, alors que Composio attend
# `X-API-Key`. Seul le remplacement global accepte un en-tete quelconque — d'ou
# la fusion ci-dessous, qui est la piece delicate de tout ce fichier.

NOM_SERVEUR_MCP = "composio"
# Le secret vit dans le .env de Hermes ; la configuration ne porte que le renvoi.
# C'est la convention de Hermes pour ses propres serveurs MCP, pas un detour.
ENV_CLE_MCP = "MCP_COMPOSIO_API_KEY"
ENTETE_MCP = {"X-API-Key": f"${{{ENV_CLE_MCP}}}"}

# Composio a deprecie ses serveurs MCP declares a la main : une session porte
# desormais son propre point MCP, et c'est la seule voie encore soutenue. On ne
# demande donc plus d'adresse au client — la cle suffit, l'adresse s'en deduit.
CHEMIN_SESSION = "/tool_router/session"


async def _adresse_mcp(cle: str, user_id: str) -> str:
    """Ouvre une session Composio et rend l'adresse MCP qu'elle expose.

    `user_id` doit etre celui des comptes connectes (cf. `connecter`) : une
    session ouverte sous un autre identifiant serait vide, et l'agent ne verrait
    aucune des applications que le client a branchees.
    """
    charge = await _appeler(
        CHEMIN_SESSION,
        cle,
        methode="POST",
        corps={"user_id": user_id},
        base=COMPOSIO_API_COMPTES,
        timeout=TIMEOUT_LONG,
    )
    mcp = charge.get("mcp") if isinstance(charge, dict) else None
    url = f"{mcp.get('url') or ''}".strip() if isinstance(mcp, dict) else ""
    if not url.startswith("https://"):
        raise HTTPException(
            status_code=502,
            detail="Composio n'a pas renvoye d'adresse MCP pour cette cle.",
        )
    return url


def fusionner_serveurs(
    existants: dict[str, Any], nom: str, entree: dict[str, Any]
) -> dict[str, Any]:
    """Ajoute un serveur MCP a la carte existante, sans en perdre un seul.

    La route de remplacement de Hermes ecrase toute la carte : renvoyer la seule
    entree Composio effacerait les autres serveurs du client. On repart donc
    toujours de la carte relue, et on n'y touche que la cle visee.

    L'entree existante du meme nom est remplacee — c'est une reconfiguration
    voulue, pas une perte : elle ne concerne que notre propre serveur.
    """
    fusionnee = {
        cle: dict(valeur) if isinstance(valeur, dict) else valeur
        for cle, valeur in (existants or {}).items()
    }
    ancienne = fusionnee.get(nom)
    if isinstance(ancienne, dict):
        # `enabled` est un choix du client : le reconfigurer ne doit pas le
        # rallumer dans son dos s'il l'avait eteint.
        conserve = {c: v for c, v in ancienne.items() if c == "enabled"}
        fusionnee[nom] = {**conserve, **entree}
    else:
        fusionnee[nom] = dict(entree)
    return fusionnee


def _carte_depuis_hermes(charge: Any) -> dict[str, Any]:
    """Rend la carte des serveurs MCP telle que Hermes la decrit.

    Hermes renvoie une liste de resumes ; le remplacement attend une carte
    nom -> configuration. On reconstruit sans inventer : un resume sans
    configuration exploitable est conserve tel quel plutot que perdu.
    """
    serveurs = charge.get("servers") if isinstance(charge, dict) else charge
    carte: dict[str, Any] = {}
    if isinstance(serveurs, dict):
        return {
            nom: dict(cfg) if isinstance(cfg, dict) else cfg
            for nom, cfg in serveurs.items()
        }
    for resume in serveurs or []:
        if not isinstance(resume, dict):
            continue
        nom = f"{resume.get('name') or ''}"
        if not nom:
            continue
        config = resume.get("config")
        carte[nom] = dict(config) if isinstance(config, dict) else _config_depuis_resume(
            resume
        )
    return carte


def _config_depuis_resume(resume: dict[str, Any]) -> dict[str, Any]:
    """Reconstruit une configuration a partir d'un resume de Hermes."""
    config: dict[str, Any] = {}
    for champ in ("url", "command", "args", "env", "headers", "auth", "enabled"):
        if champ in resume and resume[champ] is not None:
            config[champ] = resume[champ]
    return config


class BranchementMoteur(BaseModel):
    """`url` = adresse MCP imposee a la main.

    Laissee vide — le cas normal — elle est demandee a Composio a partir de la
    seule cle du client. Le champ subsiste pour les cas ou une adresse doit etre
    forcee, jamais pour le parcours courant.
    """

    url: Optional[str] = None


@router.get("/engine")
async def etat_branchement(user=Depends(get_admin_user)):
    """Composio est-il declare comme serveur MCP du moteur ?"""
    from open_webui.routers.hermes import _appeler as _appeler_hermes

    try:
        carte = _carte_depuis_hermes(await _appeler_hermes("/api/mcp/servers"))
    except HTTPException as exc:
        # Moteur muet n'est pas moteur en panne : on le dit tel quel (D27).
        return {"branche": False, "etat": "injoignable", "detail": exc.detail}
    entree = carte.get(NOM_SERVEUR_MCP)
    if not isinstance(entree, dict):
        return {"branche": False, "etat": "absent", "detail": None}
    return {
        "branche": True,
        "etat": "present",
        "actif": entree.get("enabled", True) is not False,
        "url": entree.get("url"),
        "detail": None,
    }


@router.post("/engine")
async def brancher_moteur(
    corps: Optional[BranchementMoteur] = None, user=Depends(get_admin_user)
):
    """Declare Composio comme serveur MCP du moteur.

    Sans corps — le cas normal — l'adresse est demandee a Composio a partir de
    la cle deja enregistree : le client n'a qu'une seule chose a coller.

    Trois ecritures, dans cet ordre : le secret dans le .env de Hermes, la
    relecture de la carte existante, puis son remplacement fusionne. Si la
    relecture echoue, on s'arrete — mieux vaut ne rien brancher que d'ecraser
    les serveurs MCP deja poses par le client.

    Rejouer cette route rouvre une session et rafraichit l'adresse : c'est le
    geste de reparation quand le branchement ne repond plus.
    """
    from open_webui.routers.hermes import _appeler as _appeler_hermes

    cle = await _cle_ou_erreur()
    url = (corps.url or "").strip() if corps else ""
    if not url:
        url = await _adresse_mcp(cle, user.id)
    if not url.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="L'adresse MCP de Composio doit commencer par https://.",
        )

    await _appeler_hermes(
        "/api/env", methode="PUT", corps={"key": ENV_CLE_MCP, "value": cle}
    )

    carte = _carte_depuis_hermes(await _appeler_hermes("/api/mcp/servers"))
    fusionnee = fusionner_serveurs(
        carte, NOM_SERVEUR_MCP, {"url": url, "headers": dict(ENTETE_MCP)}
    )
    await _appeler_hermes(
        "/api/mcp/servers", methode="PUT", corps={"servers": fusionnee}
    )
    return {"ok": True, "serveurs": sorted(fusionnee)}


@router.delete("/engine")
async def debrancher_moteur(user=Depends(get_admin_user)):
    """Retire le serveur MCP Composio, et lui seul.

    On passe par la suppression nominative de Hermes plutot que par un
    remplacement : rien d'autre ne peut alors disparaitre par accident.
    """
    from open_webui.routers.hermes import _appeler as _appeler_hermes

    await _appeler_hermes(f"/api/mcp/servers/{NOM_SERVEUR_MCP}", methode="DELETE")
    return {"ok": True}
