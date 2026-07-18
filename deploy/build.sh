#!/usr/bin/env bash
# Construit l'image LunarIA en 2 temps (voir Dockerfile) :
#   lunaria-base  <- app/Dockerfile d'origine (front compilé + backend)
#   lunaria-app   <- lunaria-base + agent Hermes (celle que le compose utilise)
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/2] Image de base (fork open-webui) — long au premier build (npm + pip)…"
docker build -t lunaria-base ..

echo "[2/2] Image finale (ajout de Hermes)…"
docker build -t lunaria-app .

echo "OK : image lunaria-app prête."
