"""Dépendances et helpers partagés par les routers du bridge.

Extrait de main.py (feature 012/P8) pour découper le monolithe en routers par domaine.
"""

from __future__ import annotations

import hmac
import os
import threading
import time
from collections import defaultdict

from fastapi import Header, HTTPException, Request

# --- Rate-limit basique sur les échecs d'auth (audit sécurité Basse #3, 2026-07-15) -----------
#
# Pas de middleware/lib externe (slowapi) : un compteur en mémoire, par IP, suffit à freiner un
# brute force de BRIDGE_KEY — la vraie protection réseau reste le pare-feu (cf. Haute #1). Fenêtre
# glissante + remise à zéro dès qu'une requête RÉUSSIT pour cette IP (un attaquant qui ne trouve
# jamais la clé ne se réinitialise jamais ; un appelant légitime qui échoue une fois de temps en
# temps — faute de frappe, redéploiement — n'est pas pénalisé durablement).
#
# Limites connues de cette défense (secondaire, derrière le pare-feu — grill audit phase 3,
# MOYENNE) :
#   - état en mémoire de process : un redémarrage du bridge (resync après modif) vide le
#     compteur, un attaquant qui provoque/attend un redémarrage repart avec un quota plein ;
#   - clé = IP TCP directe (pas de X-Forwarded-For, volontaire — pas de spoofing par header),
#     mais donc contournable par rotation d'adresses (un bloc IPv6, très bon marché, donne des
#     millions d'IP, chacune avec son propre quota de 20) ;
#   - ne protège qu'un seul process bridge : si le bridge tourne un jour en multi-worker, ce
#     verrou en mémoire ne serait plus partagé entre workers (compteur par worker, pas global).
# Ce n'est PAS infaillible, c'est une défense en profondeur qui freine un brute force naïf
# mono-IP mono-process ; le firewall (1 VPS par client) reste la vraie garde.
_FAILED_ATTEMPTS_WINDOW_SECONDS = 60.0
_MAX_FAILED_ATTEMPTS_PER_WINDOW = 20

_failed_attempts: dict[str, list[float]] = defaultdict(list)

# Verrou autour de la lecture-modification du compteur (grill audit phase 3, MOYENNE) :
# `require_bridge_key` est une fonction SYNCHRONE (`def`, pas `async def`) — FastAPI l'exécute
# dans le threadpool Starlette/anyio (de vrais threads OS, pas une seule boucle asyncio). Sans
# verrou, une rafale de requêtes concurrentes sur la même IP peut toutes lire le compteur encore
# sous le seuil avant qu'aucune n'ait eu le temps d'appender (TOCTOU) — le plafond de
# `_MAX_FAILED_ATTEMPTS_PER_WINDOW` n'est alors plus qu'indicatif. Le verrou sérialise l'ensemble
# lecture+décision+écriture : la section critique est courte (dict + hmac), le coût de
# contention est négligeable face à la garantie.
_rate_limit_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _purge_old_attempts(ip: str, now: float) -> list[float]:
    """Purge les tentatives hors fenêtre pour ``ip``. DOIT être appelée sous ``_rate_limit_lock``
    (pas de verrou interne ici) : c'est ``require_bridge_key`` qui délimite la section critique.
    """
    fresh = [t for t in _failed_attempts.get(ip, ()) if now - t < _FAILED_ATTEMPTS_WINDOW_SECONDS]
    _failed_attempts[ip] = fresh
    return fresh


def reset_rate_limit_state() -> None:
    """Vide l'état du limiteur — usage tests uniquement (isolation entre cas de test)."""
    with _rate_limit_lock:
        _failed_attempts.clear()


def require_bridge_key(request: Request, x_bridge_key: str | None = Header(default=None)) -> None:
    """Dépendance d'auth : exige ``X-Bridge-Key`` == ``BRIDGE_KEY`` (sinon 401).

    Lue à chaque requête (pas au chargement) pour rester testable et reconfigurable.
    Comparaison en temps constant (``hmac.compare_digest``) : le bridge peut être
    joignable depuis le réseau, on ne veut pas de fuite de la clé par timing.

    Rate-limité par IP sur les ÉCHECS uniquement (voir bloc ci-dessus) : au-delà de
    ``_MAX_FAILED_ATTEMPTS_PER_WINDOW`` échecs dans la fenêtre, renvoie 429 sans même comparer
    la clé fournie (fail-closed, ne consomme pas de cycles inutiles sur une IP déjà repérée).

    Toute la section lecture-décision-écriture du compteur est sous ``_rate_limit_lock`` (grill
    audit phase 3, MOYENNE) : ``require_bridge_key`` tourne dans le threadpool FastAPI (vrais
    threads), donc sans verrou une rafale concurrente sur la même IP pouvait dépasser le
    plafond affiché (TOCTOU). Limites connues de cette défense secondaire : état mémoire de
    process (survit pas à un redémarrage), pas de protection contre la rotation d'IP (bloc
    IPv6 bon marché) — voir le commentaire au-dessus de ``_rate_limit_lock``.
    """
    ip = _client_ip(request)
    now = time.monotonic()
    with _rate_limit_lock:
        if len(_purge_old_attempts(ip, now)) >= _MAX_FAILED_ATTEMPTS_PER_WINDOW:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "code": "too_many_attempts",
                        "message": "too many failed authentication attempts, retry later",
                    }
                },
            )

        expected = os.environ.get("BRIDGE_KEY", "")
        if not expected or not hmac.compare_digest(x_bridge_key or "", expected):
            _failed_attempts[ip].append(now)
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {"code": "unauthorized", "message": "invalid or missing bridge key"}
                },
            )

        # Succès : on efface l'historique d'échecs de cette IP (cf. rationale ci-dessus).
        _failed_attempts.pop(ip, None)


def hermes_unavailable(exc: Exception) -> HTTPException:
    """503 normalisé quand Hermes n'est pas joignable (interpréteur/fichiers absents)."""
    return HTTPException(
        status_code=503,
        detail={"error": {"code": "hermes_unavailable", "message": str(exc)}},
    )
