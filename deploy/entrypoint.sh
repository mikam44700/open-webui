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

# Espace persistant propre au moteur Codex. Il reste vide tant que Codex n'est pas
# connecté ; le créer ne touche ni au profil Hermes ni aux données de l'application.
mkdir -p "${LUNARIA_CODEX_HOME:-/app/backend/data/codex}"
chmod 700 "${LUNARIA_CODEX_HOME:-/app/backend/data/codex}"

mkdir -p "${OPENCODEX_HOME:-/app/backend/data/opencodex}"
chmod 700 "${OPENCODEX_HOME:-/app/backend/data/opencodex}"

# La sélection MCP reste pilotée par l'interface LunarIA. Codex reçoit les connecteurs
# activés compatibles ; un échec n'empêche jamais l'application de démarrer.
python -m open_webui.codex_bridge.sync_mcp \
  >>"${LUNARIA_CODEX_HOME:-/app/backend/data/codex}/mcp-sync.log" 2>&1 || true

# OpenCodex ne reçoit qu'une liste blanche de clés de FOURNISSEURS LLM. Les secrets MCP,
# la clé interne LunarIA et les tokens de canaux restent hors de son processus.
if [ "${LUNARIA_OPENCODEX_ENABLED:-0}" = "1" ]; then
  (
    # OpenCodex et App Server doivent impérativement partager le même CODEX_HOME :
    # la passerelle y injecte le catalogue multi-provider lu ensuite par Codex.
    export CODEX_HOME="${LUNARIA_CODEX_HOME:-/app/backend/data/codex}"
    provider_env="${HERMES_HOME:-/app/backend/data/hermes}/.env"
    if [ -f "${provider_env}" ]; then
      while IFS='=' read -r key value; do
        case "${key}" in
          OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|KIMI_API_KEY|ZAI_API_KEY|DEEPSEEK_API_KEY|GEMINI_API_KEY|QWEN_API_KEY|MISTRAL_API_KEY|GROQ_API_KEY|XAI_API_KEY)
            [ -n "${value}" ] && export "${key}=${value}"
            ;;
        esac
      done < "${provider_env}"
    fi
    export OCX_SERVICE=1
    python -m open_webui.codex_bridge.opencodex_config \
      >>"${OPENCODEX_HOME:-/app/backend/data/opencodex}/service.log" 2>&1
    while true; do
      set +e
      /usr/local/bin/bun run /opt/opencodex/src/cli/index.ts start --port 10100 \
        >>"${OPENCODEX_HOME:-/app/backend/data/opencodex}/service.log" 2>&1
      code=$?
      set -e
      echo "entrypoint: OpenCodex arrêté (code ${code}) — relance dans 3 s." \
        >>"${OPENCODEX_HOME:-/app/backend/data/opencodex}/service.log"
      sleep 3
    done
  ) &
fi

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

# Connecteurs MCP LunarIA (recherche-entreprises + data-gouv-fr) : déclarés AVANT le
# lancement du moteur. Hermes fige sa liste de connecteurs au démarrage (aucun rechargement
# à chaud) : une déclaration tardive (ex. pré-connexion in-app, partie 4 s trop tard le
# 2026-07-19) n'est visible qu'au démarrage SUIVANT — les agents ne voient alors pas leurs
# outils au premier boot d'une installation neuve. Idempotent, échec non bloquant (la
# pré-connexion in-app reste en filet pour le boot suivant).
python -c "from open_webui.hermes_bridge import entreprises_adapter as a; a._preconnect(attempts=1)" \
  && echo "entrypoint: connecteurs MCP LunarIA déclarés avant le moteur." \
  || echo "entrypoint: déclaration MCP avant moteur échouée (filet in-app au prochain boot)." >&2

# Moteur Hermes : garantit API_SERVER_* dans le .env, puis lance le gateway (qui porte
# le serveur de chat OpenAI-compatible sur 127.0.0.1:8642) en arrière-plan, supervisé
# par une boucle de relance simple. Le chat open-webui s'y branche via hermes_boot
# connection (plus bas). Logs dans le volume : $HERMES_HOME/logs/gateway.log.
python /app/backend/hermes_boot.py env || true
mkdir -p "${HERMES_HOME}/logs"

# Politique produit LunarIA : même le repli vers le gateway complet reste borné. Ces
# réglages vivent dans la config persistante du client et sont réappliqués après une mise
# à jour Hermes. La revue automatique des skills est désactivée dans le chat interactif :
# elle consommait le gros modèle après une réponse et pouvait concurrencer le message suivant.
"${HERMES_BIN:-hermes}" config set agent.max_turns 7 >/dev/null 2>&1 \
  || echo "entrypoint: impossible d'appliquer agent.max_turns=7" >&2
"${HERMES_BIN:-hermes}" config set skills.creation_nudge_interval 0 >/dev/null 2>&1 \
  || echo "entrypoint: impossible de désactiver la revue skills interactive" >&2

# Runtime conversationnel résident (port local 8643) : les imports Hermes et le client
# restent chauds entre deux messages. Le gateway 8642 demeure le repli universel.
(
  while true; do
    "${HERMES_PYTHON:-python}" \
      /app/backend/open_webui/hermes_bridge/hermes_runtime_server.py \
      >>"${HERMES_HOME}/logs/lunaria-runtime.log" 2>&1 &
    runtime_pid=$!
    printf '%s\n' "${runtime_pid}" > /tmp/lunaria-hermes-runtime.pid
    set +e
    wait "${runtime_pid}"
    runtime_code=$?
    set -e
    rm -f /tmp/lunaria-hermes-runtime.pid
    echo "entrypoint: runtime Hermes arrêté (code ${runtime_code}) — relance dans 2 s." \
      >>"${HERMES_HOME}/logs/lunaria-runtime.log"
    sleep 2
  done
) &

(
  find_gateway_pid() {
    for proc_dir in /proc/[0-9]*; do
      [ -r "${proc_dir}/cmdline" ] || continue
      cmdline=$(tr '\000' ' ' < "${proc_dir}/cmdline" 2>/dev/null || true)
      case "${cmdline}" in
        *hermes*gateway\ run*) printf '%s\n' "${proc_dir##*/}"; return 0 ;;
      esac
    done
    return 1
  }
  while true; do
    # `hermes update` peut relancer lui-même le gateway avec `--replace`. Il ne s'agit
    # alors plus d'un enfant de cette boucle : on l'adopte en le surveillant au lieu
    # d'essayer d'en démarrer un second toutes les 10 secondes.
    if existing_pid=$(find_gateway_pid); then
      printf '%s\n' "${existing_pid}" > /tmp/lunaria-hermes-gateway.pid
      while kill -0 "${existing_pid}" 2>/dev/null; do sleep 2; done
      rm -f /tmp/lunaria-hermes-gateway.pid
      continue
    fi
    "${HERMES_BIN:-hermes}" gateway run >>"${HERMES_HOME}/logs/gateway.log" 2>&1 &
    gateway_pid=$!
    printf '%s\n' "${gateway_pid}" > /tmp/lunaria-hermes-gateway.pid
    set +e
    wait "${gateway_pid}"
    gateway_code=$?
    set -e
    rm -f /tmp/lunaria-hermes-gateway.pid
    echo "entrypoint: gateway Hermes arrêté (code ${gateway_code}) — relance dans 10 s." >>"${HERMES_HOME}/logs/gateway.log"
    sleep 10
  done
) &

(
  agents_ok=""
  connection_ok=""
  apikey_ok=""
  competences_ok=""
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
    # Compétences métier livrées (SPEC-competences-livrees) : le client n'ouvre jamais
    # un onglet Compétences vide. Idempotent et NON DESTRUCTIF — une compétence déjà
    # présente (ou modifiée par le patron) n'est jamais écrasée.
    if [ -z "${competences_ok}" ] && python /app/backend/seed_competences.py >>/tmp/seed_agents.log 2>&1; then
      competences_ok=1
      echo "entrypoint: compétences métier en place (seed_competences.py OK)."
    fi
    [ -n "${agents_ok}" ] && [ -n "${connection_ok}" ] && [ -n "${apikey_ok}" ] \
      && [ -n "${competences_ok}" ] && exit 0
    sleep 5
  done
  echo "entrypoint: seed incomplet après 5 min — voir /tmp/seed_agents.log" >&2
) &

cd /app/backend
exec bash start.sh
