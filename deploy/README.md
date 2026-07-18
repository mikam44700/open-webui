# Déploiement LunarIA (Docker)

Une seule stack, deux modes : `local` (ton poste) et `vps` (le client). Seul le
fichier `.env` change. Crawl4AI est pré-connecté au démarrage — le client n'installe
rien (SPEC-deploiement-docker-local-vps).

## Règle projet : UNE SEULE adresse

Tout vit sur **`http://localhost:3000`** — jamais deux apps en même temps (règle actée
dans EtapeParEtape.md après le bug du conteneur fantôme). Donc :

- **Développer** : serveurs dev (dev.sh + vite) sur 3000. La stack Docker est arrêtée.
- **Tester la version client** : arrêter le dev (Ctrl+C), puis `./up.sh` — la même
  adresse sert maintenant la version client. `down` pour revenir au dev.

`up.sh` refuse de démarrer si le port est occupé (et n'arrête jamais le dev lui-même).

## Local (démo / test)

```bash
cd app/deploy
./up.sh            # génère .env, build les images (long la 1re fois), lance tout
```

Puis ouvrir `http://localhost:3000` — créer le compte admin, renseigner une clé API
de modèle, discuter. La lecture web approfondie marche sans rien installer.

## VPS client

Prérequis : un VPS avec Docker + un nom de domaine dont le DNS (enregistrement A)
pointe vers le VPS.

```bash
git clone https://github.com/mikam44700/open-webui.git lunaria
cd lunaria/deploy
./up.sh vps        # 1er passage : crée .env puis s'arrête
# éditer .env : LUNARIA_DOMAIN=lunaria.monclient.fr
./up.sh vps        # build + lancement, HTTPS automatique (Let's Encrypt)
```

Le client ouvre `https://lunaria.monclient.fr`, crée son compte : tout est déjà branché.

## Commandes utiles

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml ps       # état
docker compose -f docker-compose.yml -f docker-compose.local.yml logs -f  # logs
docker compose -f docker-compose.yml -f docker-compose.local.yml down     # arrêt
# (mode vps : remplacer local par vps)
```

Les données (comptes, conversations, config Hermes) vivent dans le volume
`lunaria-data` : elles survivent aux arrêts, redémarrages et reconstructions d'image.
`down` ne supprime PAS les volumes (jamais utiliser `down -v` chez un client).

## Sécurité (résumé)

- Secrets (`WEBUI_SECRET_KEY`, `CRAWL4AI_API_TOKEN`) générés par `up.sh` dans
  `.env` (mode 600, ignoré par git). Jamais commités.
- Crawl4AI : aucun port publié — joignable uniquement depuis le réseau Docker
  interne, et protégé par token même en interne. Conteneur durci (cap_drop ALL,
  read-only, no-new-privileges).
- Mode local : l'app n'écoute que sur 127.0.0.1. Mode vps : seul Caddy (80/443)
  est exposé.
