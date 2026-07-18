"""Pack de synchronisation du coffre (feature 005 US5) — le « 1 clic » côté client.

Génère un PACK Syncthing PRÉ-APPAIRÉ : le client le télécharge, lance l'installeur, et son
Syncthing se connecte tout seul au coffre du VPS (zéro QR, zéro Device ID à coller).

Principe : on crée une identité client fraîche (``syncthing generate``), on l'INSCRIT sur le
serveur Syncthing EN MARCHE via son API REST (pas d'édition de config à chaud — une instance
vivante ne recharge pas config.xml), on partage le dossier coffre avec elle, puis on emballe
l'identité + l'installeur dans un zip.

Le serveur est provisionné par ``deploy/syncthing-vault-sync-install.sh`` (home dédié).
"""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import httpx

# Durcissement anti-XXE (CWE-611) sur le parsing XML : ``defusedxml`` est une dépendance
# OBLIGATOIRE du bridge (déclarée dans pyproject.toml), pas un filet optionnel — c'est la
# seule protection anti-XXE réellement maintenable. Un ancien repli stdlib fait maison
# (``ET.XMLParser().parser.SetParamEntityParsing(...)``) s'est révélé cassé (AttributeError,
# ``.parser`` n'existe plus) sur Python 3.11, 3.13 ET 3.14 : il ne s'agissait pas d'un filet
# de secours théorique mais du SEUL chemin qui s'exécutait réellement tant que la dépendance
# n'était pas déclarée, et il plantait sur tout XML, bénin ou non. On ne réintroduit pas ce
# genre de repli fragile : si ``defusedxml`` venait à manquer malgré tout (install cassée),
# on échoue explicitement (``MissingDefusedXml``) plutôt qu'en silence avec une exception
# non prévue. NB : ``defusedxml.ElementTree`` n'expose QUE les fonctions de lecture
# (parse/fromstring/iterparse) — on garde ``xml.etree.ElementTree`` (ET) pour la CONSTRUCTION
# (SubElement, ElementTree(...).write(...)), qui ne parse aucune donnée entrante et ne
# présente donc aucun risque XXE.
try:
    from defusedxml.common import DefusedXmlException
    from defusedxml.ElementTree import parse as _defused_parse

    _HAS_DEFUSEDXML = True
except ImportError:  # pragma: no cover - protégé par la dépendance obligatoire (pyproject.toml)
    _HAS_DEFUSEDXML = False
    DefusedXmlException = ET.ParseError  # placeholder valide pour le tuple `except` plus bas


class MissingDefusedXml(RuntimeError):
    """``defusedxml`` est une dépendance obligatoire du bridge (protection anti-XXE, CWE-611)
    et n'est pas installée dans cet environnement. Erreur explicite plutôt qu'un plantage
    silencieux type ``AttributeError`` au fond d'un repli stdlib fait maison."""


def _safe_parse(path: Path) -> ET.ElementTree:
    """Parse un ``config.xml`` en bloquant toute résolution d'entité externe (XXE, CWE-611).

    Les 3 XML lus par ce module (config serveur déjà provisionné, config client fraîchement
    générée par ``syncthing generate``) ne transitent aujourd'hui par aucune requête HTTP
    tierce — mais ce parsing est durci par construction plutôt que par hypothèse de confiance
    sur la source, au cas où une évolution future ferait transiter du XML externe ici.
    """
    if not _HAS_DEFUSEDXML:
        raise MissingDefusedXml(
            "defusedxml est requis pour parser du XML en sécurité (protection anti-XXE, "
            "CWE-611) mais n'est pas installé dans cet environnement — voir la dépendance "
            "obligatoire déclarée dans pyproject.toml."
        )
    return _defused_parse(path)


# Home Syncthing du serveur (celui posé par le script de provisioning). Surchargables en env.
SYNC_HOME = Path(os.environ.get("SYNCTHING_HOME", os.path.expanduser("~/.config/lunaria-syncthing")))
FOLDER_ID = os.environ.get("SYNC_FOLDER_ID", "coffre")
# Où le coffre atterrit chez le client (chemin local sur SA machine).
CLIENT_VAULT = os.environ.get("SYNC_CLIENT_VAULT", "~/LunarIA/Coffre")
# Installeurs client livrés dans le pack (un par plateforme). Le client lance celui de son OS.
_DEPLOY = Path(__file__).resolve().parent.parent.parent / "deploy"
_INSTALLERS = {
    "install.sh": "lunaria-sync-client-install.sh",  # macOS / Linux
    "install.ps1": "lunaria-sync-client-install.ps1",  # Windows (PowerShell)
    "install.bat": "lunaria-sync-client-install.bat",  # Windows (double-clic)
}


class SyncUnavailable(RuntimeError):
    """La synchro n'est pas prête (Syncthing non provisionné/non démarré sur ce serveur)."""


def _server_config() -> tuple[str, str, str]:
    """(gui_url, api_key, server_device_id) lus dans le config.xml du serveur."""
    cfg = SYNC_HOME / "config.xml"
    if not cfg.exists():
        raise SyncUnavailable("Syncthing n'est pas provisionné sur ce serveur (config absente).")
    root = _safe_parse(cfg).getroot()
    gui = root.find("gui")
    addr = gui.findtext("address") if gui is not None else None
    api_key = gui.findtext("apikey") if gui is not None else None
    device = root.find("device")
    device_id = device.get("id") if device is not None else None
    if not (addr and api_key and device_id):
        raise SyncUnavailable("Config Syncthing serveur incomplète.")
    return f"http://{addr}", api_key, device_id


def is_available() -> bool:
    """La synchro est-elle provisionnée sur CE serveur ? (config Syncthing présente et lisible)

    Permet à l'UI de ne proposer « Connecter mon coffre » que là où le pack peut réellement être
    généré : ailleurs (poste de dev, serveur sans Syncthing), le bouton ne doit pas exister plutôt
    que d'échouer en 503 sous le nez du dirigeant.
    """
    try:
        _server_config()
        return True
    except (SyncUnavailable, OSError, ET.ParseError, DefusedXmlException, MissingDefusedXml):
        return False


def _client(api_key: str) -> httpx.Client:
    return httpx.Client(headers={"X-API-Key": api_key}, timeout=8.0)


def _register_client_on_server(gui_url: str, api_key: str, client_id: str) -> None:
    """Inscrit le device client sur le serveur EN MARCHE + partage le dossier coffre avec lui (REST)."""
    with _client(api_key) as c:
        # Serveur joignable ?
        try:
            c.get(f"{gui_url}/rest/system/ping").raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise SyncUnavailable("Le service Syncthing du serveur ne répond pas.") from exc
        # Inscription + partage : toute erreur HTTP ici doit remonter comme SyncUnavailable
        # (message propre au front), jamais comme une HTTPStatusError brute (500 non maîtrisée).
        try:
            # Ajouter le device client (adresse dynamique : c'est lui qui se connecte au serveur).
            c.put(
                f"{gui_url}/rest/config/devices/{client_id}",
                json={"deviceID": client_id, "name": "poste-client", "addresses": ["dynamic"]},
            ).raise_for_status()
            # Partager le dossier coffre avec ce device.
            r = c.get(f"{gui_url}/rest/config/folders/{FOLDER_ID}")
            if r.status_code == 404:
                raise SyncUnavailable(f"Dossier '{FOLDER_ID}' introuvable côté serveur.")
            r.raise_for_status()
            folder = r.json()
            devices = folder.get("devices", [])
            if not any(d.get("deviceID") == client_id for d in devices):
                devices.append({"deviceID": client_id, "introducedBy": ""})
                folder["devices"] = devices
                c.put(f"{gui_url}/rest/config/folders/{FOLDER_ID}", json=folder).raise_for_status()
        except SyncUnavailable:
            raise  # le 404 « dossier introuvable » garde son message spécifique
        except httpx.HTTPError as exc:
            raise SyncUnavailable("Le serveur Syncthing a refusé la configuration du partage.") from exc


def _gen_client_identity() -> Path:
    """Crée une identité Syncthing client fraîche (cert/clé/Device ID) dans un home temporaire."""
    home = Path(tempfile.mkdtemp(prefix="lunaria-client-"))
    subprocess.run(
        ["syncthing", "generate", f"--home={home}"],
        check=True, capture_output=True, timeout=30,
    )
    return home


def _patch_client_config(home: Path, server_id: str, gui_port: int = 8385) -> None:
    """Config client : connaît le serveur (dynamique/découverte) + partage le coffre en local."""
    cfg = home / "config.xml"
    root = _safe_parse(cfg).getroot()
    root.find("gui/address").text = f"127.0.0.1:{gui_port}"
    for tag in ("startBrowser", "crashReportingEnabled"):
        e = root.find(f"options/{tag}")
        if e is not None:
            e.text = "false"
    self_id = root.find("device").get("id")
    # Device serveur (adresse dynamique → trouvé par découverte via son Device ID).
    d = ET.SubElement(root, "device", {"id": server_id, "name": "coffre-vps", "compression": "metadata",
                                       "introducer": "false", "skipIntroductionRemovals": "false", "introducedBy": ""})
    ET.SubElement(d, "address").text = "dynamic"
    for k, v in [("paused", "false"), ("autoAcceptFolders", "false"), ("maxSendKbps", "0"),
                 ("maxRecvKbps", "0"), ("maxRequestKiB", "0"), ("untrusted", "false"),
                 ("remoteGUIPort", "0"), ("numConnections", "0")]:
        ET.SubElement(d, k).text = v
    # Dossier coffre partagé (chemin LOCAL chez le client).
    f = ET.SubElement(root, "folder", {"id": FOLDER_ID, "label": "Coffre LunarIA", "path": CLIENT_VAULT,
                                       "type": "sendreceive", "rescanIntervalS": "3600",
                                       "fsWatcherEnabled": "true", "fsWatcherDelayS": "10", "ignorePerms": "false"})
    ET.SubElement(f, "filesystemType").text = "basic"
    for did in (self_id, server_id):
        dd = ET.SubElement(f, "device", {"id": did, "introducedBy": ""})
        ET.SubElement(dd, "encryptionPassword").text = ""
    ET.SubElement(f, "minDiskFree", {"unit": "%"}).text = "1"
    ET.SubElement(f, "markerName").text = ".stfolder"
    ET.SubElement(f, "maxConflicts").text = "10"
    ET.ElementTree(root).write(cfg, encoding="utf-8", xml_declaration=False)


def _zip_pack(home: Path) -> bytes:
    """Emballe l'identité client + l'installeur + une notice dans un zip (bytes)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("config.xml", "cert.pem", "key.pem"):
            z.write(home / name, name)
        for arc, fname in _INSTALLERS.items():
            src = _DEPLOY / fname
            if src.exists():
                z.writestr(arc, src.read_text())
        z.writestr(
            "LISEZMOI.txt",
            "LunarIA Sync — votre coffre sur votre ordinateur\n\n"
            "WINDOWS  : double-cliquez sur « install.bat ».\n"
            "MAC/LINUX : dans un Terminal ouvert sur ce dossier, lancez « bash install.sh ».\n\n"
            f"Ensuite, votre coffre apparaît dans le dossier « LunarIA/Coffre » et reste synchronisé.\n"
            "Ouvrez-le dans Obsidian (« Ouvrir un dossier comme coffre »).\n\n"
            "La connexion est déjà configurée : aucune manipulation technique.\n",
        )
    return buf.getvalue()


def generate_client_pack() -> tuple[str, bytes]:
    """Retourne (nom_fichier, contenu_zip) d'un pack client pré-appairé au coffre du serveur."""
    gui_url, api_key, server_id = _server_config()
    home = _gen_client_identity()
    try:
        client_id = _safe_parse(home / "config.xml").getroot().find("device").get("id")
        _register_client_on_server(gui_url, api_key, client_id)
        _patch_client_config(home, server_id)
        return "lunaria-sync-client.zip", _zip_pack(home)
    finally:
        # Nettoyage du home temporaire (l'identité vit désormais dans le zip).
        for p in sorted(home.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        home.rmdir()
