#!/usr/bin/env bash
# Construit l'image LunarIA en 2 temps (voir Dockerfile) :
#   lunaria-base  <- app/Dockerfile d'origine (front compilé + backend)
#   lunaria-app   <- lunaria-base + agent Hermes (celle que le compose utilise)
set -euo pipefail
cd "$(dirname "$0")"

# Garde-fou memoire : builder pendant que la stack tourne fait echouer `npm run build`
# ("cannot allocate memory"). Docker Desktop plafonne la VM (~8 Go) et le build seul en
# demande jusqu'a 4 Go (NODE_OPTIONS dans le Dockerfile). On refuse plutot que de planter
# au milieu. Contournement explicite : LUNARIA_BUILD_FORCE=1 ./build.sh
if [[ "${LUNARIA_BUILD_FORCE:-0}" != "1" ]]; then
  actifs="$(docker compose -f docker-compose.yml -f docker-compose.local.yml ps -q 2>/dev/null || true)"
  if [[ -n "$actifs" ]]; then
    echo "ERREUR : la stack LunarIA tourne encore." >&2
    echo "  Le build a besoin de toute la memoire disponible : arrete-la d'abord," >&2
    echo "  puis relance le build et remonte la stack :" >&2
    echo >&2
    echo "    docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.local.yml stop" >&2
    echo "    ./deploy/build.sh && ./deploy/up.sh" >&2
    echo >&2
    echo "  (stop, PAS down -v : les donnees restent intactes)" >&2
    exit 1
  fi
fi

echo "[1/2] Image de base (fork open-webui) — long au premier build (npm + pip)…"
docker build -t lunaria-base ..

echo "[2/2] Image finale (ajout de Hermes)…"
docker build -t lunaria-app .

echo "OK : image lunaria-app prête."
