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

# Skills LunarIA (SPEC-agent-veille) : réinstallées à CHAQUE démarrage depuis l'image
# (versionnées dans le repo, comme le règlement des agents) — les nôtres seulement,
# jamais les skills ajoutées par l'utilisateur dans le volume.
if [ -n "${HERMES_HOME:-}" ] && [ -d /app/backend/hermes_skills ]; then
  mkdir -p "${HERMES_HOME}/skills"
  cp -a /app/backend/hermes_skills/. "${HERMES_HOME}/skills/"
  # Le moteur met en cache la liste des skills dans .skills_prompt_snapshot.json.
  # Comme on (ré)installe nos skills à chaque démarrage, on invalide ce cache pour
  # forcer un re-scan complet : sinon les agents ne « voient » pas nos skills
  # (moteur de Léa, veille de Sacha, GPS/actions de Luna, pont Notes) et improvisent.
  rm -f "${HERMES_HOME}/.skills_prompt_snapshot.json"
  echo "entrypoint: skills LunarIA installées + cache skills invalidé (re-scan forcé)."
fi

# Moteur Hermes : garantit API_SERVER_* dans le .env, puis lance le gateway (qui porte
# le serveur de chat OpenAI-compatible sur 127.0.0.1:8642) en arrière-plan, supervisé
# par une boucle de relance simple. Le chat open-webui s'y branche via hermes_boot
# connection (plus bas). Logs dans le volume : $HERMES_HOME/logs/gateway.log.
python /app/backend/hermes_boot.py env || true
mkdir -p "${HERMES_HOME}/logs"
(
  while true; do
    "${HERMES_BIN:-hermes}" gateway run >>"${HERMES_HOME}/logs/gateway.log" 2>&1
    echo "entrypoint: gateway Hermes arrêté (code $?) — relance dans 10 s." >>"${HERMES_HOME}/logs/gateway.log"
    sleep 10
  done
) &

(
  agents_ok=""
  connection_ok=""
  apikey_ok=""
  for _ in $(seq 1 60); do
    if [ -z "${agents_ok}" ] && python /app/backend/seed_agents.py >>/tmp/seed_agents.log 2>&1; then
      agents_ok=1
      echo "entrypoint: équipe d'agents en place (seed_agents.py OK)."
    fi
    if [ -z "${connection_ok}" ] && python /app/backend/hermes_boot.py connection >>/tmp/seed_agents.log 2>&1; then
      connection_ok=1
      echo "entrypoint: connexion chat → moteur Hermes branchée (hermes_boot OK)."
    fi
    # Pont Notes (SPEC-agents-mains-sur-app) : seed de la clé interne dès que le compte
    # admin du patron existe. Sans clé (LUNARIA_INTERNAL_API_KEY absent), le script sort
    # en échec et on continue — le pont Notes est simplement inactif sur cet environnement.
    if [ -z "${apikey_ok}" ] && python /app/backend/seed_api_key.py >>/tmp/seed_agents.log 2>&1; then
      apikey_ok=1
      echo "entrypoint: pont Notes branché (clé interne seedée)."
    fi
    [ -n "${agents_ok}" ] && [ -n "${connection_ok}" ] && [ -n "${apikey_ok}" ] && exit 0
    sleep 5
  done
  echo "entrypoint: seed incomplet après 5 min — voir /tmp/seed_agents.log" >&2
) &

cd /app/backend
exec bash start.sh
