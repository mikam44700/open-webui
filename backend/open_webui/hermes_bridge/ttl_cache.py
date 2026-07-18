"""Cache mémoire à TTL, thread-safe — mutualise le pattern catalogue des fournisseurs.

Le bridge tourne sous uvicorn : les endpoints ``def`` (synchrones) s'exécutent dans un
threadpool, donc plusieurs requêtes lisent/écrivent ces caches en concurrence. Chaque
fournisseur ré-implémentait le même dict module-level ``{"…": None, "ts": 0.0}`` SANS
verrou (thundering herd : N requêtes simultanées déclenchent N fetchs réseau identiques).
Cette classe centralise le motif avec un verrou.

Trois opérations, calquées sur le besoin réel des fetchers :
  - ``fresh(key)`` : la valeur si présente ET non expirée, sinon ``None``.
  - ``last(key)``  : la dernière valeur mémorisée MÊME expirée — pour le repli offline
                     (« réseau KO → on garde le dernier bon catalogue »). ``None`` si rien.
  - ``store(value, key)`` : mémorise + horodate.

``key=None`` → cache global mono-entrée (openrouter, kilocode…). Passer une clé
(``base_url``, ``api_key``…) → cache multi-entrées par clé.
"""

from __future__ import annotations

import threading
import time

_GLOBAL = "__global__"


class TTLCache:
    def __init__(self, ttl: float) -> None:
        self._ttl = float(ttl)
        self._data: dict = {}  # key -> (value, stored_at)
        self._lock = threading.Lock()

    def fresh(self, key=None, *, now: float | None = None):
        """Valeur non expirée pour ``key``, sinon ``None``."""
        k = _GLOBAL if key is None else key
        t = time.time() if now is None else now
        with self._lock:
            entry = self._data.get(k)
            if entry is not None and (t - entry[1]) < self._ttl:
                return entry[0]
            return None

    def last(self, key=None):
        """Dernière valeur mémorisée pour ``key`` (même expirée), ``None`` si jamais stockée."""
        k = _GLOBAL if key is None else key
        with self._lock:
            entry = self._data.get(k)
            return entry[0] if entry is not None else None

    def store(self, value, key=None, *, now: float | None = None) -> None:
        """Mémorise ``value`` pour ``key`` avec l'horodatage courant."""
        k = _GLOBAL if key is None else key
        t = time.time() if now is None else now
        with self._lock:
            self._data[k] = (value, t)

    def clear(self) -> None:
        """Vide tout le cache (utilisé par les tests pour forcer un re-fetch)."""
        with self._lock:
            self._data.clear()
