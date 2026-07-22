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
    && git -C /opt/hermes-agent checkout -B main ${HERMES_COMMIT} \
    && python -m venv /opt/hermes-agent/venv \
    && /opt/hermes-agent/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/hermes-agent/venv/bin/pip install --no-cache-dir -e /opt/hermes-agent

# uv/uvx dans le venv Hermes : les serveurs MCP en stdio se lancent via uvx.
# aiohttp : requis par la plateforme api_server du gateway (le serveur de chat
# OpenAI-compatible sur 8642) — version épinglée sur celle du pyproject Hermes (CVE fixes).
# mcp : le SDK client MCP (avec transport HTTP/SSE streamable_http). ABSENT du package
# hermes-agent alors que nos MCP (data.gouv.fr, crawl4ai) sont en HTTP/SSE — sans lui,
# AUCUN MCP ne se connecte ("streamable_http not available"). Les agents n'ont alors pas
# accès à leurs intégrations. Version alignée sur l'API non dépréciée (mcp >= 1.24).
RUN /opt/hermes-agent/venv/bin/pip install --no-cache-dir uv "aiohttp==3.14.1" "mcp==1.27.2"

# Agent Reach : couche de sélection/diagnostic des sources publiques. Version figée au
# commit validé — jamais d'installation dynamique sur le VPS client. Seuls ses canaux
# publics sans compte sont exposés par notre MCP `sources-publiques` (web, YouTube,
# RSS, GitHub) ; aucun shell général ni cookie social n'est donné aux agents.
ARG AGENT_REACH_REPO=https://github.com/Panniantong/Agent-Reach.git
ARG AGENT_REACH_COMMIT=1494c2ab239e7355a77e7cceaf3271453a1f34b5
RUN git clone --filter=blob:none ${AGENT_REACH_REPO} /opt/agent-reach \
    && git -C /opt/agent-reach checkout ${AGENT_REACH_COMMIT} \
    && /opt/hermes-agent/venv/bin/pip install --no-cache-dir -e /opt/agent-reach

# Bibliothèques documents pour Max (SPEC-agent-documents), dans le python de l'APP
# (celui qui exécute doc_cli.py) : Word (python-docx) et PDF (xhtml2pdf, pur Python,
# aucune dépendance système). Excel (openpyxl) et PowerPoint (python-pptx) sont déjà
# fournis par les dépendances open-webui — on n'installe que le manquant.
RUN pip install --no-cache-dir python-docx==1.2.0 xhtml2pdf==0.2.17

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

# Atelier documents de Théo (SPEC-atelier-documents-officecli).
#
# OfficeCLI : Word, Excel, PowerPoint. Apache-2.0, binaire autonome de 33 Mo, aucune
# suite Office requise. Il expose un serveur MCP en stdio (même mode que nos connecteurs
# recherche-entreprises et bodacc) et sait SE RELIRE : `view <fichier> issues` détecte
# les débordements de texte et propose la correction — c'est ce qui manquait quand un
# titre coupé en plein mot est parti chez le patron (2026-07-20).
#
# Typst : les PDF. Apache-2.0, 15 Mo, compile la même source en PDF ou en image (donc
# relecture possible). OfficeCLI n'exporte pas en PDF sans greffon.
#
# TARGETARCH est fourni par Docker (arm64 sur le Mac de Michael, amd64 sur un VPS
# client) : le binaire est choisi au build, JAMAIS figé — sinon l'image ne marche que
# sur une architecture. Empreintes vérifiées : un binaire altéré fait échouer le build.
ARG TARGETARCH
ARG OFFICECLI_VERSION=v1.0.139
ARG OFFICECLI_SHA_ARM64=39008c7f76d202858637810553ef14e2cd3e7f61485fdcf2011f26967a7babd1
ARG OFFICECLI_SHA_AMD64=da07d4f787d7c85724104294ac023c89971ddfaee93ebb183b289282b8f869cc
ARG TYPST_VERSION=v0.15.1
ARG TYPST_SHA_ARM64=5aa8d74a3d906e60ea12a66ac2f37f8eef1b14cbad7182a745e393a10c23dcee
ARG TYPST_SHA_AMD64=a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c
RUN set -eu; \
    if [ "${TARGETARCH}" = "arm64" ]; then \
      oc_suffixe=arm64; oc_sha="${OFFICECLI_SHA_ARM64}"; \
      ty_cible=aarch64-unknown-linux-musl; ty_sha="${TYPST_SHA_ARM64}"; \
    else \
      oc_suffixe=x64; oc_sha="${OFFICECLI_SHA_AMD64}"; \
      ty_cible=x86_64-unknown-linux-musl; ty_sha="${TYPST_SHA_AMD64}"; \
    fi; \
    curl -fsSL -o /usr/local/bin/officecli \
      "https://github.com/iOfficeAI/OfficeCLI/releases/download/${OFFICECLI_VERSION}/officecli-linux-${oc_suffixe}"; \
    echo "${oc_sha}  /usr/local/bin/officecli" | sha256sum -c -; \
    chmod 0755 /usr/local/bin/officecli; \
    curl -fsSL -o /tmp/typst.tar.xz \
      "https://github.com/typst/typst/releases/download/${TYPST_VERSION}/typst-${ty_cible}.tar.xz"; \
    echo "${ty_sha}  /tmp/typst.tar.xz" | sha256sum -c -; \
    tar -xJf /tmp/typst.tar.xz -C /tmp; \
    mv "/tmp/typst-${ty_cible}/typst" /usr/local/bin/typst; \
    chmod 0755 /usr/local/bin/typst; \
    rm -rf /tmp/typst.tar.xz "/tmp/typst-${ty_cible}"; \
    officecli --version && typst --version

# HERMES_HOME vit DANS le volume de données open-webui (/app/backend/data) :
# config.yaml, .env (tokens) et mémoires survivent aux redémarrages et aux MAJ d'image.
ENV HERMES_HOME=/app/backend/data/hermes \
    HERMES_INSTALL_DIR=/opt/hermes-agent \
    HERMES_PYTHON=/opt/hermes-agent/venv/bin/python \
    HERMES_BIN=/opt/hermes-agent/venv/bin/hermes

# Le venv Hermes en FIN de PATH : hermes/uv/uvx trouvables partout, sans jamais masquer
# le python/uvicorn de l'app (qui restent prioritaires en tête de PATH).
ENV PATH="${PATH}:/opt/hermes-agent/venv/bin"

# Entrypoint : seed de la config Hermes (1er démarrage) + seed de l'équipe, puis start.sh.
COPY --chmod=0755 entrypoint.sh /lunaria-entrypoint.sh
CMD ["bash", "/lunaria-entrypoint.sh"]
