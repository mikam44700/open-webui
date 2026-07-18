#!/usr/bin/env bash
# Lancement DEV du backend LunarIA (fork open-webui) depuis app/backend/.
# - Clé secrète lue depuis .webui_secret_key (générée au premier lancement)
# - CORS ouvert pour l'interface vite (port 3000)
# - `python -m uvicorn` : insensible au déplacement du venv (shebangs cassés sinon)
cd "$(dirname "$0")"

# Règle projet « une seule URL » (localhost:3000 = stack Docker LunarIA) :
# les serveurs dev ne démarrent JAMAIS pendant que la stack tourne.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^lunaria-'; then
  echo "STOP : la stack Docker LunarIA tourne déjà sur localhost:3000." >&2
  echo "Une seule app à la fois. L'arrêter d'abord :" >&2
  echo "  cd ../deploy && docker compose -f docker-compose.yml -f docker-compose.local.yml stop" >&2
  exit 1
fi

if [ ! -f .webui_secret_key ]; then
  head -c 12 /dev/random | base64 > .webui_secret_key
fi
export WEBUI_SECRET_KEY="$(cat .webui_secret_key)"

export CORS_ALLOW_ORIGIN="${CORS_ALLOW_ORIGIN:-http://localhost:3000;http://localhost:5173;http://localhost:8080}"
PORT="${PORT:-8080}"
./.venv/bin/python3 -m uvicorn open_webui.main:app --port "$PORT" --host 127.0.0.1 --reload
