"""Endpoints OAuth « 1 clic » centralisé (feature 016).

Expose le moteur ``oauth_engine`` via l'API REST du bridge. Le flow est centralisé :
le client clique « Se connecter » (auth-url) puis « Autoriser » chez le fournisseur,
qui le redirige vers la route callback du front ; le code est échangé contre un token
(exchange). Le ``redirect_uri`` est déterminé CÔTÉ SERVEUR (jamais par le client) et
pointe vers le front sur le seul port 3000 (cf. mémoire single-port-only).

Aucun secret ni token n'est jamais renvoyé au client.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from .. import hermes_adapter, oauth_engine
from ..deps import hermes_unavailable, require_bridge_key
from ..schemas import OAuthExchangeBody

router = APIRouter(dependencies=[Depends(require_bridge_key)])

# URI de redirection enregistrée chez les fournisseurs (route callback du front, port 3000 unique).
# Surchargeable en production via la variable d'environnement OAUTH_REDIRECT_URI.
_DEFAULT_REDIRECT = "http://localhost:3000/integrations/oauth/callback"


def _redirect_uri() -> str:
    """URI de redirection OAuth, déterminée côté serveur (jamais fournie par le client)."""
    return os.environ.get("OAUTH_REDIRECT_URI", _DEFAULT_REDIRECT)


@router.get("/integrations/oauth/{provider_id}/auth-url")
def oauth_auth_url(provider_id: str) -> dict:
    """URL d'autorisation à ouvrir côté client (1er clic « Se connecter »)."""
    try:
        return {"auth_url": oauth_engine.build_auth_url(provider_id, _redirect_uri())}
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/integrations/oauth/{provider_id}/exchange")
def oauth_exchange(provider_id: str, body: OAuthExchangeBody) -> dict:
    """Échange le code reçu au retour de redirection ; renvoie l'état réel confirmé."""
    try:
        ok = oauth_engine.exchange_code(provider_id, body.code, body.state)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"state": "connected" if ok else "not_connected"}


@router.get("/integrations/oauth/{provider_id}/status")
def oauth_status(provider_id: str) -> dict:
    """État réel de la connexion OAuth (présence du token, jamais présumé)."""
    try:
        return {"state": oauth_engine.token_status(provider_id)}
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.delete("/integrations/oauth/{provider_id}")
def oauth_disconnect(provider_id: str) -> dict:
    """Déconnecte le fournisseur (supprime le token local)."""
    try:
        oauth_engine.disconnect(provider_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"state": "not_connected"}
