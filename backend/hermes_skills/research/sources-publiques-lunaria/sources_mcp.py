#!/usr/bin/env python3
"""MCP de lecture publique contrôlée, alimenté par Agent Reach.

Pas de commande arbitraire : cinq opérations de lecture bornées. Les contenus externes
sont des données non fiables, jamais des instructions pour l'agent.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import feedparser
from agent_reach.channels.web import WebChannel
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sources-publiques")
TIMEOUT = 35
# Keep public pages inline in the agent context. Larger payloads are externalized
# by Hermes, forcing extra search/read turns and making a one-fact lookup take a
# minute. 12k chars is enough for the useful body of a normal official page.
MAX_TEXT = 12_000
UA = "LunarIA-public-research/1.0"
YTDLP = "/opt/hermes-agent/venv/bin/yt-dlp"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _http_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _github_release(url: str) -> dict | None:
    """Resolve a GitHub release page through the public API (HTML often 403s)."""
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/releases/tag/([^/?#]+)",
        url,
    )
    if not match:
        return None
    owner, repo, requested_tag = (urllib.parse.unquote(part) for part in match.groups())
    api_root = f"https://api.github.com/repos/{owner}/{repo}/releases"
    try:
        release = _http_json(f"{api_root}/tags/{urllib.parse.quote(requested_tag, safe='')}")
    except Exception:
        releases = _http_json(f"{api_root}?per_page=30")
        needle = requested_tag.lower().lstrip('v')
        release = next(
            (
                row
                for row in releases
                if needle in str(row.get('tag_name') or '').lower()
                or needle in str(row.get('name') or '').lower()
            ),
            None,
        )
    if not isinstance(release, dict):
        return {'url': url, 'erreur': 'Release GitHub officielle introuvable.'}
    return {
        'url': release.get('html_url') or url,
        'tag': release.get('tag_name'),
        'titre': release.get('name'),
        'publie_le': release.get('published_at'),
        'cree_le': release.get('created_at'),
        'contenu': str(release.get('body') or '')[:MAX_TEXT],
    }


@mcp.tool()
def lire_page_publique(url: str) -> str:
    """Lit UNE page publique et renvoie au plus 12k caractères utiles. Ne pas rappeler cet outil sur la même URL."""
    if not url.startswith(("http://", "https://")):
        return _json({"erreur": "URL publique HTTP(S) requise."})
    try:
        github_release = _github_release(url)
        if github_release is not None:
            return _json(github_release)
        text = WebChannel().read(url)
        return _json({"url": url, "contenu": text[:MAX_TEXT], "tronque": len(text) > MAX_TEXT})
    except Exception as exc:  # noqa: BLE001
        return _json({"url": url, "erreur": f"Page inaccessible : {exc}. Ne rien inventer."})


@mcp.tool()
def lire_video_youtube(url: str) -> str:
    """Récupère métadonnées et sous-titres d'une vidéo YouTube publique, sans télécharger la vidéo."""
    if not url.startswith(("https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
        return _json({"erreur": "URL YouTube publique requise."})
    try:
        with tempfile.TemporaryDirectory(prefix="lunaria-youtube-") as work:
            output = str(Path(work) / "video.%(ext)s")
            cmd = [
                YTDLP, "--dump-single-json", "--no-simulate", "--skip-download", "--write-auto-subs",
                "--write-subs", "--sub-langs", "fr,en", "--sub-format", "vtt",
                "-o", output, url,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
            if proc.returncode != 0:
                return _json({"url": url, "erreur": "Vidéo ou transcription inaccessible. Ne pas résumer son contenu."})
            data = json.loads(proc.stdout)
            tracks = list(Path(work).glob("*.vtt"))
            transcript = ""
            if tracks:
                raw = tracks[0].read_text(encoding="utf-8", errors="replace")
                lines = []
                previous = ""
                for line in raw.splitlines():
                    line = re.sub(r"<[^>]+>", "", line).strip()
                    if not line or line == "WEBVTT" or "-->" in line or line.isdigit():
                        continue
                    if line != previous:
                        lines.append(line)
                        previous = line
                transcript = "\n".join(lines)[:MAX_TEXT]
            return _json({
                "url": url,
                "titre": data.get("title"),
                "auteur": data.get("uploader"),
                "date": data.get("upload_date"),
                "duree_secondes": data.get("duration"),
                "transcription_disponible": bool(transcript),
                "transcription": transcript or None,
                "note": None if transcript else "Aucune transcription récupérée : ne pas inventer le contenu de la vidéo.",
            })
    except Exception as exc:  # noqa: BLE001
        return _json({"url": url, "erreur": f"Lecture YouTube impossible : {exc}. Ne rien inventer."})


@mcp.tool()
def lire_flux_rss(url: str, limite: int = 15) -> str:
    """Lit les entrées récentes d'un flux RSS/Atom public."""
    if not url.startswith(("http://", "https://")):
        return _json({"erreur": "URL RSS/Atom HTTP(S) requise."})
    feed = feedparser.parse(url)
    if getattr(feed, "bozo", False) and not feed.entries:
        return _json({"url": url, "erreur": "Flux RSS inaccessible ou invalide."})
    entries = []
    for item in feed.entries[: max(1, min(int(limite), 30))]:
        entries.append({
            "titre": item.get("title"), "url": item.get("link"),
            "date": item.get("published") or item.get("updated"),
            "resume": (item.get("summary") or "")[:1_500],
        })
    return _json({"url": url, "titre": feed.feed.get("title"), "entrees": entries})


@mcp.tool()
def rechercher_github(requete: str, limite: int = 10) -> str:
    """Recherche des dépôts GitHub publics via l'API publique, en lecture seule."""
    if not requete.strip():
        return _json({"erreur": "Requête GitHub requise."})
    count = max(1, min(int(limite), 20))
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": requete.strip(), "sort": "updated", "order": "desc", "per_page": count}
    )
    try:
        data = _http_json(url)
        items = [{
            "nom": row.get("full_name"), "url": row.get("html_url"),
            "description": row.get("description"), "etoiles": row.get("stargazers_count"),
            "mis_a_jour": row.get("updated_at"),
        } for row in data.get("items", [])]
        return _json({"requete": requete, "resultats": items})
    except Exception as exc:  # noqa: BLE001
        return _json({"requete": requete, "erreur": f"GitHub inaccessible : {exc}."})


@mcp.tool()
def diagnostiquer_sources() -> str:
    """Retourne l'état des sources publiques autorisées, sans secret ni détail système."""
    checks = {"web": True, "rss": True, "github": True}
    try:
        proc = subprocess.run([YTDLP, "--version"], capture_output=True, timeout=10, check=False)
        checks["youtube"] = proc.returncode == 0
    except Exception:
        checks["youtube"] = False
    return _json({"sources": checks, "regle": "Une source indisponible doit être signalée ; ne rien inventer."})


if __name__ == "__main__":
    mcp.run()
