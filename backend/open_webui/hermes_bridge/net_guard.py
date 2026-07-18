"""Garde anti-SSRF pour les URL fournies par l'utilisateur avant un fetch côté serveur.

Le crawl (Crawl4AI) récupère une URL AVEC un navigateur headless, DEPUIS le VPS. Sans
garde, un appelant peut faire lire au serveur des cibles internes : métadonnées cloud
(169.254.169.254 → creds IAM), services de l'hôte (le bridge lui-même, le gateway Hermes),
ou tout service du réseau privé du VPS. On valide donc l'URL AVANT de la transmettre.

Principe : schéma http/https uniquement, puis on résout le nom en IP(s) et on refuse toute
IP privée / loopback / lien-local / réservée / multicast. Une URL n'est acceptée que si
TOUTES ses IP résolues sont publiques.

Limite connue (TOCTOU / DNS rebinding) : entre cette validation et le fetch réel par
Crawl4AI, la réponse DNS peut changer. On ne peut pas fermer ça complètement côté bridge
(c'est Crawl4AI qui ouvre la connexion) ; cette garde bloque le cas courant et direct.
Défense en profondeur idéale à terme : réseau Docker isolé pour le conteneur de crawl.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Type du résolveur injectable (défaut : socket.getaddrinfo) — permet des tests sans réseau.
Resolver = object


def _ip_is_blocked(ip_str: str, *, allow_private: bool = False) -> bool:
    """Vrai si l'IP est une cible à refuser pour un fetch serveur.

    ``allow_private=False`` (défaut — crawl de contenu tiers) : refuse toute IP non
    publique (privée, loopback, lien-local, réservée, multicast, non spécifiée).

    ``allow_private=True`` (instances auto-hébergées déclarées par l'utilisateur, ex.
    SearXNG/Camofox/Firecrawl qui tournent typiquement en ``localhost`` ou sur le LAN
    du VPS/client — un refus total casserait cet usage légitime) : autorise privé et
    loopback, mais refuse TOUJOURS lien-local (couvre les métadonnées cloud
    ``169.254.169.254``, qui est *aussi* classée privée par ``ipaddress``), multicast,
    non spécifiée, et réservée (sauf la loopback IPv6 ``::1``, que Python classe à tort
    en « réservée » alors qu'elle doit rester autorisée au même titre que ``127.0.0.1``).
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # illisible = on refuse par principe
    # IPv6 encapsulant une IPv4 (::ffff:169.254.169.254) : juger sur l'IPv4 sous-jacente.
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped

    always_blocked = (
        ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or (ip.is_reserved and not ip.is_loopback)
    )
    if allow_private:
        return always_blocked
    return always_blocked or ip.is_private or ip.is_loopback


def _check_url(url: str, *, allow_private: bool, resolver) -> bool:
    """Logique partagée : schéma http/https + résolution DNS + toutes les IP acceptables.

    ``allow_private`` bascule entre le mode strict (``is_public_http_url``, refuse tout
    privé) et le mode self-hosted (``is_safe_self_hosted_url``, autorise privé/loopback).
    """
    try:
        parsed = urlparse(url)
    except Exception:  # noqa: BLE001 — URL pathologique : on refuse
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    host = parsed.hostname
    if not host:
        return False

    # Hôte déjà écrit comme IP littérale (http://169.254.169.254/...) : pas de DNS à faire.
    try:
        ipaddress.ip_address(host)
        return not _ip_is_blocked(host, allow_private=allow_private)
    except ValueError:
        pass  # ce n'est pas une IP → c'est un nom, on résout ci-dessous

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = resolver(host, port, proto=socket.IPPROTO_TCP)
    except Exception:  # noqa: BLE001 — DNS injoignable / nom inexistant
        return False

    if not infos:
        return False
    # Refuser si UNE SEULE des IP résolues est bloquée (empêche un nom qui mêle
    # une IP acceptée et une IP interdite).
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            return False
        if _ip_is_blocked(sockaddr[0], allow_private=allow_private):
            return False
    return True


def is_public_http_url(url: str, *, resolver=socket.getaddrinfo) -> bool:
    """Vrai si ``url`` est http(s), a un hôte, et résout UNIQUEMENT vers des IP publiques.

    ``resolver`` est injectable (signature de ``socket.getaddrinfo``) pour les tests.
    Toute anomalie (schéma non http, hôte absent, résolution en échec, IP non publique)
    renvoie False — jamais d'exception.

    Usage : fetch de contenu TIERS non maîtrisé (crawl) — refus strict de tout privé.
    """
    return _check_url(url, allow_private=False, resolver=resolver)


def is_safe_self_hosted_url(url: str, *, resolver=socket.getaddrinfo) -> bool:
    """Vrai si ``url`` est http(s) et ne pointe pas vers une cible dangereuse.

    Garde-fou PROPORTIONNÉ pour les instances auto-hébergées déclarées par l'utilisateur
    (SearXNG/Camofox/Firecrawl, cf. ``tool_connection_adapter._FIELD_TEST['url_ping']``) :
    ces services tournent couramment en ``localhost`` ou sur le réseau privé du VPS/LAN
    client — un ``is_public_http_url`` classique (qui refuse TOUT privé) casserait cet
    usage légitime pour 100 % des déploiements. On autorise donc privé/loopback, mais on
    refuse toujours lien-local (couvre les métadonnées cloud ``169.254.169.254``),
    multicast, non spécifiée et réservée — c'est-à-dire tout ce qui n'est *jamais* une
    cible self-hosted légitime, y compris pour un attaquant qui détournerait ce champ.

    Ne PAS utiliser pour un fetch de contenu tiers non maîtrisé (crawl) : pour ça,
    ``is_public_http_url`` (refus strict de tout privé) reste la règle.
    """
    return _check_url(url, allow_private=True, resolver=resolver)
