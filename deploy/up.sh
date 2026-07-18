#!/usr/bin/env bash
# Lance la stack LunarIA. Usage : ./up.sh [local|vps]   (défaut : local)
#
# Premier lancement : génère deploy/.env avec les secrets (clé de session de l'app +
# token Crawl4AI) — critère 4 de la spec : aucun secret dans git, génération auto.
# Mode vps : exige LUNARIA_DOMAIN dans .env (le domaine du client, DNS déjà pointé).
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-local}"
if [[ "$MODE" != "local" && "$MODE" != "vps" ]]; then
  echo "usage: ./up.sh [local|vps]" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Premier lancement : génération des secrets dans deploy/.env"
  {
    echo "# Généré par up.sh — NE PAS committer (couvert par .gitignore)."
    echo "WEBUI_SECRET_KEY=$(openssl rand -hex 32)"
    echo "CRAWL4AI_API_TOKEN=$(openssl rand -hex 32)"
    echo "# Port local (mode local uniquement)"
    echo "LUNARIA_PORT=3000"
    echo "# Domaine du client (mode vps uniquement), ex. lunaria.monclient.fr"
    echo "LUNARIA_DOMAIN="
  } > .env
  chmod 600 .env
fi

if [[ "$MODE" == "vps" ]] && ! grep -Eq '^LUNARIA_DOMAIN=.+$' .env; then
  echo "Renseigner LUNARIA_DOMAIN dans deploy/.env puis relancer ./up.sh vps" >&2
  exit 1
fi

# Règle projet : UNE SEULE adresse (http://localhost:3000) et une seule app à la fois.
# Si le port est occupé (serveur de dev vite/uvicorn), on explique au lieu d'empiler
# une deuxième app — et on ne tue JAMAIS un processus existant nous-mêmes.
if [[ "$MODE" == "local" ]]; then
  PORT="$(grep -E '^LUNARIA_PORT=' .env | cut -d= -f2)"
  PORT="${PORT:-3000}"
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN | grep -qv "com.docke"; then
    echo "Le port $PORT est déjà utilisé (probablement ton serveur de dev)." >&2
    echo "Règle projet : une seule app à la fois sur http://localhost:$PORT." >&2
    echo "→ Arrête le dev (Ctrl+C dans les terminaux vite / dev.sh), puis relance ./up.sh" >&2
    exit 1
  fi
fi

if ! docker image inspect lunaria-app >/dev/null 2>&1; then
  ./build.sh
fi

docker compose -f docker-compose.yml -f "docker-compose.$MODE.yml" up -d

echo
if [[ "$MODE" == "local" ]]; then
  PORT="$(grep -E '^LUNARIA_PORT=' .env | cut -d= -f2)"
  echo "LunarIA démarre : http://localhost:${PORT:-3000} (1re fois : ~1 min le temps que tout monte)"
else
  DOMAIN="$(grep -E '^LUNARIA_DOMAIN=' .env | cut -d= -f2)"
  echo "LunarIA démarre : https://${DOMAIN} (certificat émis automatiquement au 1er accès)"
fi
