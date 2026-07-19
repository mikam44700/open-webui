# syntax=docker/dockerfile:1
# Image finale LunarIA = app (fork open-webui) + agent Hermes embarqué.
#
# Se construit en 2 temps (voir build.sh) :
#   1. docker build -t lunaria-base ..     <- app/Dockerfile d'origine (front + backend)
#   2. docker build -t lunaria-app .       <- cette image : ajoute Hermes par-dessus
#
# Pourquoi 2 temps : app/Dockerfile est le fichier upstream open-webui — on ne le modifie
# pas (zéro conflit aux merges upstream), on empile Hermes dans une image dérivée.
ARG BASE_IMAGE=lunaria-base
FROM ${BASE_IMAGE}

# Hermes épinglé au commit validé sur le poste de Michael (jamais un tag flottant :
# ce que le client reçoit est exactement ce qui a été testé).
ARG HERMES_REPO=https://github.com/NousResearch/hermes-agent.git
ARG HERMES_COMMIT=0bf44d557f4564c9d7d84cbf7632b02015f00271

# Même disposition qu'une installation locale (~/.hermes/hermes-agent + venv) : le bridge
# retrouve l'interpréteur via HERMES_PYTHON et la CLI via HERMES_BIN.
RUN git clone --filter=blob:none ${HERMES_REPO} /opt/hermes-agent \
    && git -C /opt/hermes-agent checkout ${HERMES_COMMIT} \
    && python -m venv /opt/hermes-agent/venv \
    && /opt/hermes-agent/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/hermes-agent/venv/bin/pip install --no-cache-dir -e /opt/hermes-agent

# uv/uvx dans le venv Hermes : les serveurs MCP (dont data.gouv.fr) se lancent via uvx.
# aiohttp : requis par la plateforme api_server du gateway (le serveur de chat
# OpenAI-compatible sur 8642) — version épinglée sur celle du pyproject Hermes (CVE fixes).
RUN /opt/hermes-agent/venv/bin/pip install --no-cache-dir uv "aiohttp==3.14.1"

# Moteur de recherche sociale last30days (MIT, mvanhorn) pour la skill veille-lunaria
# (agent Sacha, SPEC-agent-veille) : sources libres uniquement (Reddit, HN, YouTube,
# arXiv...), AUCUNE clé embarquée — l'image reste le template neutre des VPS clients.
# Le moteur exige Python 3.12+ (l'app reste en 3.11) : CPython géré par uv, hors PATH.
# yt-dlp : transcriptions YouTube du moteur. SETUP_COMPLETE court-circuite son wizard.
ARG LAST30DAYS_REPO=https://github.com/mvanhorn/last30days-skill.git
ARG LAST30DAYS_COMMIT=249c7a4c040558a903d6838dee31012980d4946d
RUN git clone --filter=blob:none ${LAST30DAYS_REPO} /opt/last30days \
    && git -C /opt/last30days checkout ${LAST30DAYS_COMMIT} \
    && uv python install 3.12 \
    && /opt/hermes-agent/venv/bin/pip install --no-cache-dir yt-dlp \
    && mkdir -p /root/.config/last30days \
    && printf 'SETUP_COMPLETE=true\n' > /root/.config/last30days/.env \
    && chmod 600 /root/.config/last30days/.env

# HERMES_HOME vit DANS le volume de données open-webui (/app/backend/data) :
# config.yaml, .env (tokens) et mémoires survivent aux redémarrages et aux MAJ d'image.
ENV HERMES_HOME=/app/backend/data/hermes \
    HERMES_PYTHON=/opt/hermes-agent/venv/bin/python \
    HERMES_BIN=/opt/hermes-agent/venv/bin/hermes

# Le venv Hermes en FIN de PATH : hermes/uv/uvx trouvables partout, sans jamais masquer
# le python/uvicorn de l'app (qui restent prioritaires en tête de PATH).
ENV PATH="${PATH}:/opt/hermes-agent/venv/bin"

# Entrypoint : seed de la config Hermes (1er démarrage) + seed de l'équipe, puis start.sh.
COPY --chmod=0755 entrypoint.sh /lunaria-entrypoint.sh
CMD ["bash", "/lunaria-entrypoint.sh"]
