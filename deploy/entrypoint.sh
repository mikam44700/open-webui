#!/usr/bin/env bash
# Entrypoint LunarIA (SPEC-stack-complete) : prépare Hermes et l'équipe, puis lance l'app.
#
# 1. Seed du HERMES_HOME (premier démarrage d'un volume neuf uniquement) : recopie la
#    config apportée par le bind-mount /hermes-seed (rempli par up.sh depuis ~/.hermes,
#    COPIE — l'original du poste n'est jamais touché). Un volume déjà initialisé
#    (config.yaml présent) n'est JAMAIS écrasé : sa mémoire/config prime.
# 2. Seed de l'équipe d'agents (Luna, Mike, Victor, Léa) : seed_agents.py est idempotent
#    mais exige que les migrations open-webui aient créé la table `model` — on boucle en
#    arrière-plan jusqu'à ce qu'il passe, pendant que l'app démarre normalement.
# 3. exec du start.sh open-webui d'origine (PID 1 reste l'app, arrêt propre du conteneur).
set -euo pipefail

if [ -n "${HERMES_HOME:-}" ] && [ ! -f "${HERMES_HOME}/config.yaml" ] && [ -f /hermes-seed/config.yaml ]; then
  echo "entrypoint: premier démarrage — reprise de la config Hermes depuis le seed."
  mkdir -p "${HERMES_HOME}"
  cp -a /hermes-seed/. "${HERMES_HOME}/"
fi

(
  for _ in $(seq 1 60); do
    if python /app/backend/seed_agents.py >>/tmp/seed_agents.log 2>&1; then
      echo "entrypoint: équipe d'agents en place (seed_agents.py OK)."
      exit 0
    fi
    sleep 5
  done
  echo "entrypoint: seed_agents.py n'est pas passé en 5 min — voir /tmp/seed_agents.log" >&2
) &

cd /app/backend
exec bash start.sh
