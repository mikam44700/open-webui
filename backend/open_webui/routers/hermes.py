"""Router Hermes — LunarIA V2.

Le moteur Hermes tourne dans un conteneur separe. Le backend ne peut donc ni lire
`~/.hermes`, ni executer la commande `hermes` comme le faisait la V1 : tout passe
par l'API HTTP d'Hermes, jointe par le reseau interne de Docker.

Ce router est un intermediaire. Il ne stocke rien, ne decide rien : il relaie les
appels du navigateur vers Hermes en y ajoutant la cle d'acces, que le navigateur
ne voit jamais.

Deux regles de securite tenues ici :
  1. La cle d'API d'Hermes reste cote serveur. Elle est ajoutee a la volee.
  2. Tout est reserve a l'administrateur (`get_admin_user`), comme en V1.
"""

import logging
import os
from typing import Any, Optional
from urllib.parse import quote

import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

# Hermes expose deux surfaces, et la distinction compte :
#
#   - l'API de conversation (port 8642), compatible OpenAI, protegee par cle.
#     Elle ne sert que `/v1/...` — c'est par la que passe le chat.
#   - le tableau de bord (port 9119), qui porte les donnees de la page Moteur :
#     outils, MCP, messagerie, competences. Il s'authentifie par session.
#
# Aucun des deux n'est publie vers la machine. Seul ce backend les atteint.
HERMES_API_URL = os.environ.get("HERMES_API_URL", "http://hermes:8642").rstrip("/")
def _lire_cle_api() -> str:
    """Cle d'acces au moteur.

    La variable d'environnement prime. A defaut, on relit le fichier de
    configuration de Hermes, deja monte en lecture seule dans le conteneur :
    la cle n'a alors pas a etre recopiee a la main dans un second endroit,
    ou elle finirait par diverger.
    """
    cle = os.environ.get("HERMES_API_KEY", "")
    chemin = os.environ.get("HERMES_CONFIG_FILE", "")
    if cle or not chemin:
        return cle

    try:
        import yaml

        with open(chemin, encoding="utf-8") as fichier:
            config = yaml.safe_load(fichier) or {}
        return str(
            config.get("platforms", {})
            .get("api_server", {})
            .get("extra", {})
            .get("key", "")
        )
    except (OSError, AttributeError, TypeError, ValueError) as erreur:
        log.warning("Cle du moteur illisible dans %s : %s", chemin, erreur)
        return ""


HERMES_API_KEY = _lire_cle_api()

HERMES_DASHBOARD_URL = os.environ.get(
    "HERMES_DASHBOARD_URL", "http://hermes-dashboard:9119"
).rstrip("/")
HERMES_DASHBOARD_USER = os.environ.get("HERMES_DASHBOARD_USER", "")
HERMES_DASHBOARD_PASSWORD = os.environ.get("HERMES_DASHBOARD_PASSWORD", "")

# Hermes repond vite sur ses lectures, mais certains appels (catalogue MCP,
# inventaire des outils) interrogent des sources distantes.
TIMEOUT_COURT = aiohttp.ClientTimeout(total=10)
TIMEOUT_LONG = aiohttp.ClientTimeout(total=45)

# Session partagee vers le tableau de bord. Elle porte les cookies obtenus a la
# connexion : sans elle, il faudrait se reconnecter a chaque appel, soit une
# poignee d'allers-retours inutiles a chaque ouverture d'onglet.
_session_tableau: Optional[aiohttp.ClientSession] = None


def _entetes() -> dict[str, str]:
    entetes = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        entetes["Authorization"] = f"Bearer {HERMES_API_KEY}"
    return entetes


async def _session_authentifiee() -> aiohttp.ClientSession:
    """Rend une session connectee au tableau de bord, en la creant au besoin."""
    global _session_tableau

    if _session_tableau is None or _session_tableau.closed:
        _session_tableau = aiohttp.ClientSession(timeout=TIMEOUT_LONG)
        await _connecter(_session_tableau)

    return _session_tableau


async def _connecter(session: aiohttp.ClientSession) -> None:
    """Ouvre une session sur le tableau de bord avec le compte de service."""
    if not HERMES_DASHBOARD_USER or not HERMES_DASHBOARD_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Le compte de service du moteur n'est pas configure.",
        )
    try:
        async with session.post(
            f"{HERMES_DASHBOARD_URL}/auth/password-login",
            json={
                "provider": "basic",
                "username": HERMES_DASHBOARD_USER,
                "password": HERMES_DASHBOARD_PASSWORD,
            },
        ) as reponse:
            if reponse.status >= 400:
                raise HTTPException(
                    status_code=502,
                    detail="Le moteur a refuse le compte de service.",
                )
    except aiohttp.ClientError as exc:
        log.warning(f"Tableau de bord Hermes injoignable: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Le moteur Hermes ne repond pas. Verifiez qu'il est demarre.",
        )


async def _appeler(
    chemin: str,
    methode: str = "GET",
    corps: Optional[dict] = None,
    timeout: aiohttp.ClientTimeout = TIMEOUT_COURT,
) -> Any:
    """Relaie un appel vers Hermes et rend sa reponse telle quelle.

    Le chemin decide de la surface interrogee : `/v1/...` part vers l'API de
    conversation, tout le reste vers le tableau de bord.

    Les erreurs sont traduites en messages lisibles : l'utilisateur de la page
    Moteur n'a pas a dechiffrer une trace technique.
    """
    vers_api = chemin.startswith("/v1/")

    if vers_api:
        url = f"{HERMES_API_URL}{chemin}"
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    methode, url, headers=_entetes(), json=corps
                ) as reponse:
                    return await _lire(reponse, methode, chemin)
        except aiohttp.ClientError as exc:
            log.warning(f"Moteur injoignable sur {url}: {exc}")
            raise HTTPException(
                status_code=503,
                detail="Le moteur Hermes ne repond pas. Verifiez qu'il est demarre.",
            )
        except TimeoutError:
            raise HTTPException(
                status_code=504, detail="Le moteur met trop de temps a repondre."
            )

    url = f"{HERMES_DASHBOARD_URL}{chemin}"
    session = await _session_authentifiee()
    try:
        async with session.request(methode, url, json=corps) as reponse:
            # Session expiree : Hermes la fait tourner toutes les 12 heures. On
            # se reconnecte une fois plutot que de renvoyer une erreur a l'ecran.
            if reponse.status == 401:
                await _connecter(session)
                async with session.request(methode, url, json=corps) as seconde:
                    return await _lire(seconde, methode, chemin)
            return await _lire(reponse, methode, chemin)
    except aiohttp.ClientError as exc:
        log.warning(f"Tableau de bord injoignable sur {url}: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Le moteur Hermes ne repond pas. Verifiez qu'il est demarre.",
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504, detail="Le moteur met trop de temps a repondre."
        )


async def _lire(reponse: aiohttp.ClientResponse, methode: str, chemin: str) -> Any:
    """Traduit une reponse Hermes en donnees, ou en erreur lisible."""
    if reponse.status >= 400:
        log.warning(f"Hermes {methode} {chemin} -> {reponse.status}")
        detail = None
        try:
            charge = await reponse.json(content_type=None)
            if isinstance(charge, dict):
                detail = charge.get("detail") or charge.get("message")
        except Exception:
            pass
        raise HTTPException(
            status_code=reponse.status,
            detail=detail or f"Le moteur a refuse la demande ({reponse.status}).",
        )
    texte = await reponse.text()
    if not texte:
        return None
    try:
        return await reponse.json(content_type=None)
    except Exception:
        return {"texte": texte}


# --------------------------------------------------------------------------
# Etat general du moteur
# --------------------------------------------------------------------------


class EtatMoteur(BaseModel):
    joignable: bool
    version: Optional[str] = None
    modele_actif: Optional[str] = None
    fournisseur_actif: Optional[str] = None
    detail: Optional[str] = None


@router.get("/status", response_model=EtatMoteur)
async def etat_du_moteur(user=Depends(get_admin_user)):
    """Le moteur repond-il, et avec quel modele travaille-t-il ?

    Cet appel ne doit jamais faire echouer la page : si le moteur est arrete,
    on renvoie `joignable: false` avec l'explication, pas une erreur HTTP.
    """
    try:
        modeles = await _appeler("/v1/models")
    except HTTPException as exc:
        return EtatMoteur(joignable=False, detail=str(exc.detail))

    modele_actif = None
    fournisseur_actif = None
    if isinstance(modeles, dict):
        donnees = modeles.get("data") or []
        if donnees:
            modele_actif = donnees[0].get("id")
            fournisseur_actif = donnees[0].get("owned_by")

    version = None
    try:
        info = await _appeler("/api/model/info")
        if isinstance(info, dict):
            version = info.get("version") or info.get("hermes_version")
            modele_actif = info.get("model") or modele_actif
            fournisseur_actif = info.get("provider") or fournisseur_actif
    except HTTPException:
        # L'API du tableau de bord peut etre restreinte : l'etat reste valable.
        pass

    return EtatMoteur(
        joignable=True,
        version=version,
        modele_actif=modele_actif,
        fournisseur_actif=fournisseur_actif,
    )


# --------------------------------------------------------------------------
# Onglet « Modeles IA »
# --------------------------------------------------------------------------


class ChoixModele(BaseModel):
    model: str
    provider: Optional[str] = None


class NiveauIntelligence(BaseModel):
    effort: str


@router.get("/models/options")
async def options_de_modeles(user=Depends(get_admin_user)):
    """Le catalogue complet des modeles que le moteur sait utiliser.

    Sans ``include_unconfigured``, Hermes ne renvoie que les fournisseurs deja
    branches. La page « Modeles IA » perd alors toutes les cartes a decouvrir
    bien que leurs plugins et leurs logos soient bien installes.
    """
    return await _appeler(
        "/api/model/options?include_unconfigured=1", timeout=TIMEOUT_LONG
    )


@router.get("/models/info")
async def info_modele(user=Depends(get_admin_user)):
    """Le modele actuellement actif et ses reglages."""
    return await _appeler("/api/model/info")


@router.post("/models/set")
async def changer_de_modele(choix: ChoixModele, user=Depends(get_admin_user)):
    """Change le modele qui fait reflechir l'assistant."""
    # Hermes 0.19 exige la portée de l'affectation. Sans elle, chaque clic du
    # sélecteur du chat était rejeté en 422 avant même de changer le modèle.
    corps = {"scope": "main", **choix.model_dump(exclude_none=True)}
    return await _appeler(
        "/api/model/set", methode="POST", corps=corps
    )


@router.get("/models/reasoning")
async def niveau_intelligence(user=Depends(get_admin_user)):
    """Niveau de raisonnement réellement transmis à chaque requête Hermes."""
    return {"effort": await Config.get("lunaria.reasoning_effort", "medium")}


@router.post("/models/reasoning")
async def changer_niveau_intelligence(
    choix: NiveauIntelligence, user=Depends(get_admin_user)
):
    effort = choix.effort.strip().lower()
    if effort not in {"low", "medium", "high", "xhigh"}:
        raise HTTPException(status_code=422, detail="Niveau d'intelligence inconnu.")
    await Config.upsert({"lunaria.reasoning_effort": effort})
    return {"effort": effort, "applies_to": "new_conversations"}


# --------------------------------------------------------------------------
# Onglet « Modeles IA » — sous-onglet « Moteur »
#
# L'etat detaille du moteur : version installee, mise a jour disponible, etat
# de la passerelle. C'est le panneau « Agent Hermes » de la V1.
# --------------------------------------------------------------------------


@router.get("/engine/status")
async def etat_detaille(user=Depends(get_admin_user)):
    """Version, date de publication, mise a jour disponible, etat de la passerelle."""
    return await _appeler("/api/status", timeout=TIMEOUT_LONG)


# --------------------------------------------------------------------------
# Mise a jour du moteur
#
# On ne lance aucune commande depuis Open WebUI : c'est Hermes qui se met a
# jour lui-meme, par son API. C'est la seule facon qui marche partout — ici
# ou Hermes tourne a cote, comme sur un VPS ou il tournera dans son propre
# conteneur, hors de portee d'un shell lance d'ici.
#
# Hermes sait dans quel cas il se trouve : sa reponse porte `install_method`
# et `can_apply`, qui disent si la mise a jour peut s'appliquer en place ou
# si elle doit passer par un autre moyen.
# --------------------------------------------------------------------------


@router.get("/update/check")
async def verifier_mise_a_jour(user=Depends(get_admin_user)):
    """Regarde s'il existe une version plus recente, sans rien installer."""
    return await _appeler("/api/hermes/update/check", timeout=TIMEOUT_LONG)


@router.post("/update")
async def demarrer_mise_a_jour(user=Depends(get_admin_user)):
    """Lance la mise a jour. Hermes travaille en tache de fond et sauvegarde avant."""
    return await _appeler("/api/hermes/update", methode="POST", timeout=TIMEOUT_LONG)


@router.get("/update/status")
async def suivi_mise_a_jour(user=Depends(get_admin_user)):
    """Avancement de la mise a jour en cours, avec les dernieres lignes du journal."""
    return await _appeler("/api/actions/hermes-update/status", timeout=TIMEOUT_COURT)


# --------------------------------------------------------------------------
# Onglet « Modeles IA » — sous-onglets de connexion
#
# La V1 rangeait les fournisseurs par mode de connexion : par compte (OAuth),
# par cle collee, par serveur local. On reprend ce decoupage.
# --------------------------------------------------------------------------


@router.get("/providers/oauth")
async def fournisseurs_par_compte(user=Depends(get_admin_user)):
    """Fournisseurs auxquels on se connecte avec un compte."""
    return await _appeler("/api/providers/oauth", timeout=TIMEOUT_LONG)


@router.post("/providers/oauth/{provider_id}/start")
async def demarrer_oauth(provider_id: str, user=Depends(get_admin_user)):
    """Demarre le parcours de connexion par compte natif de Hermes."""
    identifiant = quote(provider_id, safe="")
    return await _appeler(
        f"/api/providers/oauth/{identifiant}/start",
        methode="POST",
        timeout=TIMEOUT_LONG,
    )


@router.post("/providers/oauth/{provider_id}/submit")
async def soumettre_oauth(
    provider_id: str, corps: dict, user=Depends(get_admin_user)
):
    """Transmet le code d'un parcours OAuth qui en demande un."""
    identifiant = quote(provider_id, safe="")
    return await _appeler(
        f"/api/providers/oauth/{identifiant}/submit",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.get("/providers/oauth/{provider_id}/poll/{session_id}")
async def suivre_oauth(
    provider_id: str, session_id: str, user=Depends(get_admin_user)
):
    """Suit une connexion OAuth sans exposer le jeton obtenu."""
    fournisseur = quote(provider_id, safe="")
    session = quote(session_id, safe="")
    return await _appeler(
        f"/api/providers/oauth/{fournisseur}/poll/{session}",
        timeout=TIMEOUT_LONG,
    )


@router.delete("/providers/oauth/sessions/{session_id}")
async def annuler_oauth(session_id: str, user=Depends(get_admin_user)):
    session = quote(session_id, safe="")
    return await _appeler(
        f"/api/providers/oauth/sessions/{session}",
        methode="DELETE",
        timeout=TIMEOUT_LONG,
    )


@router.delete("/providers/oauth/{provider_id}")
async def deconnecter_oauth(provider_id: str, user=Depends(get_admin_user)):
    identifiant = quote(provider_id, safe="")
    return await _appeler(
        f"/api/providers/oauth/{identifiant}",
        methode="DELETE",
        timeout=TIMEOUT_LONG,
    )


@router.get("/providers/keys")
async def cles_fournisseurs(user=Depends(get_admin_user)):
    """Liste seulement l'etat et la valeur masquee des cles connues."""
    return await _appeler("/api/env", timeout=TIMEOUT_LONG)


@router.post("/providers/keys/validate")
async def verifier_cle(corps: dict, user=Depends(get_admin_user)):
    """Verifie une cle chez son fournisseur avant de l'enregistrer."""
    return await _appeler(
        "/api/providers/validate",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.put("/providers/keys/{key}")
async def enregistrer_cle(key: str, corps: dict, user=Depends(get_admin_user)):
    """Enregistre une cle dans le coffre .env de Hermes."""
    valeur = str(corps.get("value") or "")
    return await _appeler(
        "/api/env",
        methode="PUT",
        corps={"key": key, "value": valeur},
        timeout=TIMEOUT_LONG,
    )


@router.delete("/providers/keys/{key}")
async def retirer_cle(key: str, user=Depends(get_admin_user)):
    """Retire une cle et ses anciens miroirs de configuration."""
    return await _appeler(
        "/api/env",
        methode="DELETE",
        corps={"key": key},
        timeout=TIMEOUT_LONG,
    )


@router.get("/providers/endpoints")
async def serveurs_personnalises(user=Depends(get_admin_user)):
    """Serveurs locaux ou adresses personnalisees declares dans le moteur."""
    return await _appeler("/api/providers/custom-endpoints", timeout=TIMEOUT_LONG)


@router.post("/providers/endpoints/validate")
async def verifier_serveur(corps: dict, user=Depends(get_admin_user)):
    return await _appeler(
        "/api/providers/custom-endpoints/validate",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.post("/providers/endpoints")
async def enregistrer_serveur(corps: dict, user=Depends(get_admin_user)):
    return await _appeler(
        "/api/providers/custom-endpoints",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.post("/providers/endpoints/{endpoint_id}/activate")
async def activer_serveur(endpoint_id: str, user=Depends(get_admin_user)):
    identifiant = quote(endpoint_id, safe="")
    return await _appeler(
        f"/api/providers/custom-endpoints/{identifiant}/activate",
        methode="POST",
        timeout=TIMEOUT_LONG,
    )


@router.delete("/providers/endpoints/{endpoint_id}")
async def retirer_serveur(endpoint_id: str, user=Depends(get_admin_user)):
    identifiant = quote(endpoint_id, safe="")
    return await _appeler(
        f"/api/providers/custom-endpoints/{identifiant}",
        methode="DELETE",
        timeout=TIMEOUT_LONG,
    )


@router.get("/models/moa")
async def modeles_combines(user=Depends(get_admin_user)):
    """Modeles IA combines : plusieurs cerveaux qui reflechissent ensemble."""
    return await _appeler("/api/model/moa", timeout=TIMEOUT_LONG)


# --------------------------------------------------------------------------
# Onglet « Messagerie »
# --------------------------------------------------------------------------


@router.get("/messaging/platforms")
async def plateformes_de_messagerie(user=Depends(get_admin_user)):
    """Les canaux par lesquels on peut parler a l'assistant."""
    return await _appeler("/api/messaging/platforms", timeout=TIMEOUT_LONG)


@router.put("/messaging/platforms/{platform_id}")
async def configurer_messagerie(
    platform_id: str, corps: dict, user=Depends(get_admin_user)
):
    identifiant = quote(platform_id, safe="")
    return await _appeler(
        f"/api/messaging/platforms/{identifiant}",
        methode="PUT",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.post("/messaging/platforms/{platform_id}/test")
async def tester_messagerie(platform_id: str, user=Depends(get_admin_user)):
    identifiant = quote(platform_id, safe="")
    return await _appeler(
        f"/api/messaging/platforms/{identifiant}/test",
        methode="POST",
        timeout=TIMEOUT_LONG,
    )


@router.post("/messaging/{platform_id}/onboarding/start")
async def demarrer_jumelage(
    platform_id: str, corps: dict, user=Depends(get_admin_user)
):
    identifiant = quote(platform_id, safe="")
    return await _appeler(
        f"/api/messaging/{identifiant}/onboarding/start",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.get("/messaging/{platform_id}/onboarding/{pairing_id}")
async def suivre_jumelage(
    platform_id: str, pairing_id: str, user=Depends(get_admin_user)
):
    plateforme = quote(platform_id, safe="")
    jumelage = quote(pairing_id, safe="")
    return await _appeler(
        f"/api/messaging/{plateforme}/onboarding/{jumelage}",
        timeout=TIMEOUT_LONG,
    )


@router.post("/messaging/{platform_id}/onboarding/{pairing_id}/apply")
async def appliquer_jumelage(
    platform_id: str, pairing_id: str, user=Depends(get_admin_user)
):
    plateforme = quote(platform_id, safe="")
    jumelage = quote(pairing_id, safe="")
    return await _appeler(
        f"/api/messaging/{plateforme}/onboarding/{jumelage}/apply",
        methode="POST",
        timeout=TIMEOUT_LONG,
    )


@router.delete("/messaging/{platform_id}/onboarding/{pairing_id}")
async def annuler_jumelage(
    platform_id: str, pairing_id: str, user=Depends(get_admin_user)
):
    plateforme = quote(platform_id, safe="")
    jumelage = quote(pairing_id, safe="")
    return await _appeler(
        f"/api/messaging/{plateforme}/onboarding/{jumelage}",
        methode="DELETE",
        timeout=TIMEOUT_LONG,
    )


# --------------------------------------------------------------------------
# Onglet « MCP »
# --------------------------------------------------------------------------


@router.get("/mcp/servers")
async def serveurs_mcp(user=Depends(get_admin_user)):
    """Les serveurs MCP branches sur le moteur."""
    return await _appeler("/api/mcp/servers", timeout=TIMEOUT_LONG)


@router.get("/mcp/catalog")
async def catalogue_mcp(user=Depends(get_admin_user)):
    """Le catalogue des serveurs MCP installables."""
    return await _appeler("/api/mcp/catalog", timeout=TIMEOUT_LONG)


class BasculeMcp(BaseModel):
    enabled: bool


@router.post("/mcp/servers/{nom}/enabled")
async def basculer_serveur_mcp(
    nom: str, bascule: BasculeMcp, user=Depends(get_admin_user)
):
    """Active ou desactive un serveur MCP."""
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/mcp/servers/{identifiant}/enabled",
        methode="PUT",
        corps=bascule.model_dump(),
        timeout=TIMEOUT_LONG,
    )


@router.post("/mcp/servers")
async def ajouter_serveur_mcp(corps: dict, user=Depends(get_admin_user)):
    return await _appeler(
        "/api/mcp/servers",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.put("/mcp/servers")
async def remplacer_serveurs_mcp(corps: dict, user=Depends(get_admin_user)):
    """Reecrit la carte complete des serveurs MCP.

    Hermes n'expose que ce remplacement global : la route d'ajout ne sait poser
    qu'un en-tete `Authorization: Bearer`, ce qui exclut les serveurs attendant
    un autre nom d'en-tete. Passer par ici est le seul moyen d'en configurer un.

    DANGER : cette route ECRASE tout ce qui n'est pas dans `servers`. L'appelant
    doit avoir relu la carte existante et l'avoir fusionnee au prealable. Rien
    dans ce router ne le fait a sa place.
    """
    return await _appeler(
        "/api/mcp/servers",
        methode="PUT",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.post("/mcp/servers/{nom}/test")
async def tester_serveur_mcp(nom: str, user=Depends(get_admin_user)):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/mcp/servers/{identifiant}/test",
        methode="POST",
        timeout=TIMEOUT_LONG,
    )


@router.post("/mcp/servers/{nom}/auth")
async def authentifier_serveur_mcp(nom: str, user=Depends(get_admin_user)):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/mcp/servers/{identifiant}/auth",
        methode="POST",
        timeout=TIMEOUT_LONG,
    )


@router.get("/mcp/oauth/flows/{flow_id}")
async def suivre_authentification_mcp(flow_id: str, user=Depends(get_admin_user)):
    identifiant = quote(flow_id, safe="")
    return await _appeler(
        f"/api/mcp/oauth/flows/{identifiant}",
        timeout=TIMEOUT_LONG,
    )


@router.delete("/mcp/servers/{nom}")
async def retirer_serveur_mcp(nom: str, user=Depends(get_admin_user)):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/mcp/servers/{identifiant}",
        methode="DELETE",
        timeout=TIMEOUT_LONG,
    )


@router.post("/mcp/catalog/install")
async def installer_mcp(corps: dict, user=Depends(get_admin_user)):
    return await _appeler(
        "/api/mcp/catalog/install",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


# --------------------------------------------------------------------------
# Onglets « Outils », « Integrations » et « Recherche & web »
#
# Les trois lisent le meme inventaire cote Hermes (les « toolsets ») : c'est la
# page qui les repartit par famille. Un seul appel reseau sert les trois onglets.
# --------------------------------------------------------------------------


@router.get("/tools/toolsets")
async def inventaire_des_outils(user=Depends(get_admin_user)):
    """Toutes les capacites du moteur : outils natifs, integrations, recherche web."""
    return await _appeler("/api/tools/toolsets", timeout=TIMEOUT_LONG)


class BasculeOutil(BaseModel):
    enabled: bool


@router.post("/tools/toolsets/{nom}")
async def basculer_outil(nom: str, bascule: BasculeOutil, user=Depends(get_admin_user)):
    """Active ou desactive une capacite."""
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/tools/toolsets/{identifiant}",
        methode="PUT",
        corps=bascule.model_dump(),
        timeout=TIMEOUT_LONG,
    )


@router.get("/tools/toolsets/{nom}/config")
async def configuration_outil(nom: str, user=Depends(get_admin_user)):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/tools/toolsets/{identifiant}/config",
        timeout=TIMEOUT_LONG,
    )


@router.put("/tools/toolsets/{nom}/provider")
async def choisir_fournisseur_outil(
    nom: str, corps: dict, user=Depends(get_admin_user)
):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/tools/toolsets/{identifiant}/provider",
        methode="PUT",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.put("/tools/toolsets/{nom}/env")
async def enregistrer_cles_outil(
    nom: str, corps: dict, user=Depends(get_admin_user)
):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/tools/toolsets/{identifiant}/env",
        methode="PUT",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.get("/tools/toolsets/{nom}/models")
async def modeles_outil(nom: str, user=Depends(get_admin_user)):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/tools/toolsets/{identifiant}/models",
        timeout=TIMEOUT_LONG,
    )


@router.put("/tools/toolsets/{nom}/model")
async def choisir_modele_outil(
    nom: str, corps: dict, user=Depends(get_admin_user)
):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/tools/toolsets/{identifiant}/model",
        methode="PUT",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


@router.post("/tools/toolsets/{nom}/post-setup")
async def finaliser_outil(nom: str, corps: dict, user=Depends(get_admin_user)):
    identifiant = quote(nom, safe="")
    return await _appeler(
        f"/api/tools/toolsets/{identifiant}/post-setup",
        methode="POST",
        corps=corps,
        timeout=TIMEOUT_LONG,
    )


# --------------------------------------------------------------------------
# Onglet « Competences »
# --------------------------------------------------------------------------


@router.get("/skills")
async def competences(user=Depends(get_admin_user)):
    """Les competences natives du moteur."""
    return await _appeler("/api/skills", timeout=TIMEOUT_LONG)


class BasculeCompetence(BaseModel):
    name: str
    enabled: bool


@router.post("/skills/toggle")
async def basculer_competence(
    bascule: BasculeCompetence, user=Depends(get_admin_user)
):
    """Active ou desactive une competence."""
    return await _appeler(
        "/api/skills/toggle",
        methode="PUT",
        corps=bascule.model_dump(),
        timeout=TIMEOUT_LONG,
    )


# --------------------------------------------------------------------------
# Onglet « Garde-fous »
# --------------------------------------------------------------------------


# Les garde-fous qu'on remonte, designes UN PAR UN.
#
# La premiere version cherchait des mots ("approval", "guard", "timeout") dans
# les NOMS de cles. Elle ramassait `mcp_discovery_timeout`, un simple delai
# d'attente technique, et pouvait rater un vrai garde-fou mal nomme. On nomme
# donc chaque chemin explicitement : la liste est plus courte a maintenir qu'un
# resultat faux a expliquer.
#
# Chaque entree : (identifiant, chemin dans la config, type de lecture).
# Le chemin est une suite de cles imbriquees.
GARDE_FOUS = (
    ("autorisation_avant_action", ("approvals", "mode"), "texte"),
    ("actions_automatiques", ("approvals", "cron_mode"), "texte"),
    ("confirmation_destructive", ("approvals", "destructive_slash_confirm"), "bool"),
    ("arret_si_emballement", ("tool_loop_guardrails", "hard_stop_enabled"), "bool"),
    (
        "plafond_recherches_web",
        ("tool_loop_guardrails", "loop_caps", "max_web_searches"),
        "nombre",
    ),
    ("commandes_autorisees", ("command_allowlist",), "liste"),
    ("analyse_des_commandes", ("security", "tirith_enabled"), "bool"),
    ("masquage_des_secrets", ("security", "redact_secrets"), "bool"),
    ("adresses_internes", ("security", "allow_private_urls"), "bool"),
    ("masquage_donnees_personnelles", ("privacy", "redact_pii"), "bool"),
    ("delai_max_execution", ("code_execution", "timeout"), "secondes"),
)


def _lire_chemin(config: dict, chemin: tuple) -> Any:
    """Descend une suite de cles imbriquees, sans lever si l'une manque."""
    courant: Any = config
    for cle in chemin:
        if not isinstance(courant, dict) or cle not in courant:
            return None
        courant = courant[cle]
    return courant


@router.get("/guardrails")
async def garde_fous(user=Depends(get_admin_user)):
    """Le cadre dans lequel l'agent a le droit d'agir.

    Hermes n'expose pas de route dediee : on lit sa configuration et on n'en
    remonte que les reglages d'encadrement listes ci-dessus. Aucun secret ne
    traverse — les valeurs remontees sont des booleens, des nombres et des mots
    d'etat, jamais des cles ni des identifiants.

    La mise en mots francaise se fait cote interface : ici on ne fait que
    lire, sans interpreter.
    """
    config = await _appeler("/api/config", timeout=TIMEOUT_LONG)
    if not isinstance(config, dict):
        return {"disponible": False, "regles": []}

    regles = []
    for identifiant, chemin, genre in GARDE_FOUS:
        valeur = _lire_chemin(config, chemin)
        if valeur is None:
            # Reglage absent de cette version d'Hermes : on ne l'invente pas.
            continue
        if genre == "liste" and isinstance(valeur, list):
            valeur = len(valeur)
        regles.append({"id": identifiant, "genre": genre, "valeur": valeur})

    return {"disponible": bool(regles), "regles": regles}
