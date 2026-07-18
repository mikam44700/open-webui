#!/usr/bin/env bash
# Démarrage COMPLET du mode dev LunarIA en UNE commande : backend + interface + préchauffage.
# Règle « une seule URL » (2026-07-18) : ce script ne rend la main que lorsque
# http://localhost:3000 est entièrement compilé et répond — plus jamais de page
# blanche ou clignotante au premier chargement.
# Idempotent : relançable sans risque, ne redémarre que ce qui est éteint.
set -u
cd "$(dirname "$0")"

# Garde « une seule app à la fois » : jamais pendant que la stack Docker tourne.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^lunaria-'; then
  echo "STOP : la stack Docker LunarIA tourne déjà sur localhost:3000." >&2
  echo "Une seule app à la fois. L'arrêter d'abord :" >&2
  echo "  cd deploy && docker compose -f docker-compose.yml -f docker-compose.local.yml stop" >&2
  exit 1
fi

LOG_DIR="${TMPDIR:-/tmp}/lunaria-dev"
mkdir -p "$LOG_DIR"

http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$1" 2>/dev/null; }

# 1. Backend (8080)
if [ "$(http_code http://localhost:8080/health)" = "200" ]; then
  echo "-> backend déjà en marche (8080)"
else
  echo "-> démarrage du backend (8080)…"
  nohup ./backend/dev.sh > "$LOG_DIR/backend.log" 2>&1 &
  ok=""
  for _ in $(seq 1 30); do
    sleep 2
    if [ "$(http_code http://localhost:8080/health)" = "200" ]; then ok=1; break; fi
  done
  if [ -z "$ok" ]; then
    echo "ECHEC backend — dernières lignes du log :" >&2
    tail -20 "$LOG_DIR/backend.log" >&2
    exit 1
  fi
  echo "   backend prêt."
fi

# 2. Interface vite (3000)
if [ "$(http_code http://localhost:3000)" = "200" ]; then
  echo "-> interface déjà en marche (3000)"
else
  echo "-> démarrage de l'interface (3000)… (le premier lancement peut prendre 1-2 min)"
  export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
  nohup npm run dev -- --port 3000 --host 127.0.0.1 > "$LOG_DIR/vite.log" 2>&1 &
  ok=""
  for _ in $(seq 1 60); do
    sleep 3
    if [ "$(http_code http://localhost:3000)" = "200" ]; then ok=1; break; fi
  done
  if [ -z "$ok" ]; then
    echo "ECHEC interface — dernières lignes du log :" >&2
    tail -20 "$LOG_DIR/vite.log" >&2
    exit 1
  fi
  echo "   interface prête."
fi

# 3. Préchauffage : compile les pages principales AVANT ouverture du navigateur.
echo "-> préchauffage des pages…"
for route in / /auth /hermes /workspace /workspace/agents /workspace/models; do
  curl -s -o /dev/null --max-time 120 "http://localhost:3000${route}" || true
done

echo ""
echo "PRÊT : http://localhost:3000 (pages compilées, aucun clignotement)"
echo "Logs : $LOG_DIR/backend.log et $LOG_DIR/vite.log"
