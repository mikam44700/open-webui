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
    echo "# Clé interne du pont Notes (agents → API de l'app), format sk-*"
    echo "LUNARIA_INTERNAL_API_KEY=sk-$(openssl rand -hex 32)"
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

# Presenton (SPEC-agent-documents) : complète le .env EXISTANT sans jamais l'écraser
# (installations déjà en place). La clé de modèle est à renseigner UNE fois par le
# dirigeant (fournisseur OpenAI-compatible, ex. xAI) — vide, le service tourne mais
# la génération de présentations le signalera honnêtement.
if ! grep -q '^PRESENTON_LLM_URL=' .env; then
  {
    echo "# Presenton (presentations PPTX/PDF de Max) : fournisseur OpenAI-compatible."
    echo "PRESENTON_LLM_URL=https://api.x.ai/v1"
    echo "PRESENTON_LLM_API_KEY="
    echo "PRESENTON_LLM_MODEL=grok-4-1212"
  } >> .env
  echo "Presenton : variables ajoutées à deploy/.env — renseigner PRESENTON_LLM_API_KEY."
fi

# Règle projet : UNE SEULE adresse (http://localhost:3000) et une seule app à la fois.
# Si le port est occupé (serveur de dev vite/uvicorn), on explique au lieu d'empiler
# une deuxième app — et on ne tue JAMAIS un processus existant nous-mêmes.
if [[ "$MODE" == "local" ]]; then
  PORT="$(grep -E '^LUNARIA_PORT=' .env | cut -d= -f2)"
  PORT="${PORT:-3000}"
  # tail -n +2 : saute la ligne d'en-tête de lsof (sinon la garde se déclenche à tort
  # quand SEULE la stack Docker écoute déjà — cas du redéploiement d'une nouvelle image).
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | tail -n +2 | grep -qv "com.docke"; then
    echo "Le port $PORT est déjà utilisé (probablement ton serveur de dev)." >&2
    echo "Règle projet : une seule app à la fois sur http://localhost:$PORT." >&2
    echo "→ Arrête le dev (Ctrl+C dans les terminaux vite / dev.sh), puis relance ./up.sh" >&2
    exit 1
  fi
fi

# Reprise de la config Hermes du poste (SPEC-stack-complete, critère 5) : COPIE de
# fichiers choisis de ~/.hermes vers deploy/.hermes-seed (gitignoré) — l'original du Mac
# n'est JAMAIS déplacé ni modifié. On ne copie que la config utile (jamais le code, les
# caches ni les binaires macOS). Un fichier déjà présent dans le seed n'est pas réécrasé.
mkdir -p .hermes-seed
if [[ -f "$HOME/.hermes/config.yaml" ]]; then
  for item in config.yaml .env SOUL.md skills plugins cron hooks memories; do
    if [[ -e "$HOME/.hermes/$item" && ! -e ".hermes-seed/$item" ]]; then
      cp -a "$HOME/.hermes/$item" ".hermes-seed/$item"
    fi
  done
  chmod -R go-rwx .hermes-seed
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
