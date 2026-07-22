"""Schémas du Providers Bridge.

Décrivent ce que l'API expose. Source de vérité = Hermes (voir hermes_adapter).
Cf. specs/001-providers-page/data-model.md
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel


class AuthType(str, Enum):
    api_key = "api_key"
    oauth = "oauth"
    aws_sdk = "aws_sdk"
    none = "none"


class ProviderState(str, Enum):
    not_configured = "not_configured"
    configured = "configured"
    active = "active"


class Category(str, Enum):
    """Regroupement UX par mode de connexion (cf. page Providers)."""

    oauth = "oauth"  # connexion par compte (hermes auth add) : Codex, Grok OAuth, Nous, MiniMax, Qwen
    api = "api"  # clé API à coller : Anthropic, OpenAI, OpenRouter, DeepSeek...
    local = "local"  # serveur local, base_url : LM Studio, Ollama, vLLM
    other = "other"  # cas à part : AWS Bedrock, GitHub Copilot


class Model(BaseModel):
    id: str
    label: str
    provider_id: str
    release_date: str | None = None
    family: str | None = None
    reasoning: bool | None = None
    supported_efforts: list[str] | None = None
    metadata_confidence: str = "unknown"
    # Modèle au catalogue mais refusé par l'abonnement de la clé (ex. Kimi HighSpeed hors
    # forfait Allegretto) : le front l'affiche grisé avec la raison au lieu de laisser
    # partir un appel voué à l'erreur en plein chat.
    available: bool = True
    unavailable_reason: str | None = None


class Provider(BaseModel):
    id: str
    label: str
    logo: str
    auth_type: AuthType
    category: Category
    env_key: str | None = None
    base_url: str | None = None
    state: ProviderState
    models: list[Model] = []
    catalog_source: str = "hermes_catalog"
    catalog_refresh: str = "engine_update"
    catalog_sort: str = "recent_first"


class ActiveSelection(BaseModel):
    provider_id: str
    model_id: str
    # Optionnel : uniquement porté pour que la réconciliation de ``set_active`` (hermes_adapter)
    # puisse restaurer le triplet complet (provider/default/base_url) en cas d'échec de la 3e
    # écriture, pas seulement la paire provider/default (cf. audit Haute — base_url échappait
    # à la réconciliation).
    base_url: str | None = None


class ProvidersResponse(BaseModel):
    providers: list[Provider]


# --- Connecteurs MCP (feature 002) -------------------------------------------
# Cf. specs/002-connecteurs-mcp/data-model.md


class McpTransport(str, Enum):
    stdio = "stdio"
    http = "http"
    sse = "sse"


class McpAuthType(str, Enum):
    none = "none"
    key = "key"
    oauth = "oauth"


class ConnectorState(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"
    disabled = "disabled"
    incomplete = "incomplete"
    auth_required = "auth_required"


class SecretState(str, Enum):
    present = "present"
    absent = "absent"


class Connector(BaseModel):
    id: str
    transport: McpTransport
    auth_type: McpAuthType
    enabled: bool = True
    state: ConnectorState
    endpoint: str = ""
    secret_state: SecretState = SecretState.absent
    source: str | None = None


class ConfigField(BaseModel):
    """Un champ à renseigner pour installer un MCP stdio (depuis le ``configSchema`` du manifest)."""

    key: str  # nom du champ (ex. "AIRTABLE_API_KEY", "allowedDirectories")
    label: str = ""  # libellé/description affiché
    type: str = "string"  # "string" | "array"
    secret: bool = False  # true => clé/token, saisi masqué et stocké dans .env
    required: bool = False


class CatalogEntry(BaseModel):
    name: str
    description: str = ""
    transport: McpTransport
    auth_type: McpAuthType
    installed: bool = False
    source_url: str | None = None
    config_fields: list[ConfigField] = []  # champs à demander avant install (MCP stdio à clé)
    # --- Enrichissement « registre des 55 » (feature curation MCP) ---
    label: str = ""  # nom d'affichage (ex. "Stripe") ; vide => le front retombe sur `name`
    icon_url: str | None = None  # logo distant (registre) ; le front préfère un logo local si présent
    category: str = "other"  # clé de catégorie UX (cf. mcp_curation.CATEGORY_ORDER)
    visibility: str = "visible"  # "visible" (dirigeant) | "expert" (mode avancé)
    tags: list[str] = []
    installable: bool = True  # False = présent au catalogue mais pas (encore) installable en 1 clic
    url: str | None = None  # endpoint du serveur MCP distant (registre remote) ; pour l'install 1 clic
    install_method: str = ""  # "engine" (hermes mcp install) | "registry" (custom http + OAuth) | ""


class TestResult(BaseModel):
    ok: bool
    reason: str | None = None
    tools_count: int | None = None


class ConnectorsResponse(BaseModel):
    connectors: list[Connector]


class CatalogResponse(BaseModel):
    entries: list[CatalogEntry]


# --- Capacités natives Hermes : Outils (toolsets) + Compétences (skills) -------
# Source de vérité = Hermes (config.yaml). Pilotage par introspection (cf. tools_adapter,
# skills_adapter). Gérés PAR PLATEFORME côté Hermes (cli/telegram/...).


class ToolConnectionState(str, Enum):
    """État de connexion d'un toolset (feature 003)."""

    not_required = "not_required"  # aucune connexion attendue → pas de badge
    connection_required = "connection_required"  # connexion attendue mais absente
    connected = "connected"  # credentials présents (via _toolset_has_keys)


class Toolset(BaseModel):
    """Un toolset natif Hermes (ex. ``web``, ``terminal``) activable/désactivable."""

    name: str  # clé du toolset (ex. "web")
    label: str  # libellé Hermes (peut contenir un emoji, ex. "🔍 Web Search & Scraping")
    description: str = ""  # résumé des outils inclus
    tools: list[str] = []  # outils individuels résolus (noms techniques)
    enabled: bool = True
    connection_state: ToolConnectionState = ToolConnectionState.not_required
    providers: list[str] = []  # noms lisibles des fournisseurs/backends (Exa, Firecrawl, FAL.ai…)


class Skill(BaseModel):
    """Une compétence native Hermes (dossier ``~/.hermes/skills/<name>``)."""

    name: str
    category: str | None = None
    description: str = ""
    enabled: bool = True


class CustomSkill(BaseModel):
    """Une compétence « maison » créée par le client (``~/.hermes/skills/maison/<name>``)."""

    name: str  # identifiant (slug)
    label: str  # nom lisible
    description: str = ""
    category: str = "Autres"  # rangement dans la page (Vente, Finance, SAV…)
    enabled: bool = True  # activée globalement dans le moteur (skills.disabled)


class CustomSkillsResponse(BaseModel):
    skills: list[CustomSkill]


class ToolsetsResponse(BaseModel):
    toolsets: list[Toolset]


# --- Connexion des toolsets (feature 003) ------------------------------------
# Source de vérité = Hermes (TOOL_CATEGORIES / TOOLSET_ENV_REQUIREMENTS). On ne transporte
# jamais les valeurs de secrets, seulement leur présence. Cf. specs/003-outils-connectables.


class ToolProviderKind(str, Enum):
    key = "key"  # champs à saisir (env_vars)
    oauth = "oauth"  # flux d'autorisation par compte externe
    managed = "managed"  # géré par abonnement Nous (rien à saisir)


class ToolField(BaseModel):
    """Un champ à renseigner pour connecter un toolset (issu d'un env_var Hermes)."""

    key: str  # nom de la variable (ex. "HASS_TOKEN")
    label: str  # libellé affiché (issu du prompt Hermes)
    default: str | None = None
    url: str | None = None  # lien d'aide éventuel
    secret: bool = False  # true => valeur sensible, jamais réaffichée
    present: bool = False  # la variable est-elle déjà renseignée ? (présence seule)


class ToolProvider(BaseModel):
    """Un fournisseur possible pour un toolset (depuis ``providers``)."""

    name: str
    tag: str | None = None
    badge: str | None = None
    kind: ToolProviderKind = ToolProviderKind.key
    fields: list[ToolField] = []
    slug: str | None = None  # identifiant stable pour mapper un logo côté front (ex. "exa")
    advanced: bool = False  # fournisseur technique → replié sous « Options avancées » (front)
    category: str | None = None  # regroupement en mode Expert : "free" | "self_hosted" | "paid"
    connected: bool | None = None  # état réel détecté (OAuth/abonnement) ; None = non applicable
    active: bool | None = None  # web : ce fournisseur est-il le search_backend courant ? None = n/a


class ToolConnection(BaseModel):
    """Métadonnées de connexion d'un toolset (écran « Connecter »)."""

    name: str
    required: bool = False
    connected: bool = False
    providers: list[ToolProvider] = []
    note: str | None = None  # encart d'info affiché en haut de la fenêtre (ex. vision)


class ToolOAuthStatus(BaseModel):
    """Suivi d'un flux OAuth de toolset (calqué sur le statut OAuth MCP)."""

    status: str  # running | success | error
    auth_url: str | None = None
    log: str = ""


class SkillsResponse(BaseModel):
    skills: list[Skill]


# --- Agents : profils Hermes (page Agents, ex-onglet Modèles) ------------------
# Un « agent » = un profil Hermes (``~/.hermes/profiles/<name>/``). Source de vérité = Hermes
# (introspection via ``hermes_cli.profiles``). Cf. profiles_adapter.


class Agent(BaseModel):
    """Un agent = un profil Hermes.

    - ``name`` : identifiant du profil (``default`` = ``~/.hermes`` lui-même).
    - ``description`` : résumé du rôle (``profile.yaml``), affiché sous le nom de la carte.
    - ``model`` / ``provider`` : le « cerveau » de l'agent (``config.yaml``).
    - ``active`` : c'est l'agent « de garde » (profil actif du gateway).
    - ``avatar`` : nom de fichier (ou chemin relatif) de l'image d'avatar (``profile.yaml``),
      ex. ``"mike.png"`` ; le front le résout en ``/assets/agents/mike.png``. ``None`` = pas
      d'avatar choisi. Zéro traitement d'image côté bridge : simple chaîne stockée/relue.
    """

    name: str
    description: str = ""
    model: str | None = None
    provider: str | None = None
    is_default: bool = False
    skill_count: int = 0
    gateway_running: bool = False
    active: bool = False
    avatar: str | None = None


class AgentsResponse(BaseModel):
    agents: list[Agent]


class AgentToolsResponse(BaseModel):
    """Périmètre d'outils d'un agent : compétences + connecteurs MCP, avec leur état PAR AGENT."""

    skills: list[Skill]
    mcps: list[Connector]


# --- Gateway : supervision + plateformes de messagerie ------------------------
# Page « Gateway » (portage de Hermes Desktop). Source de vérité = Hermes
# (tokens ~/.hermes/.env, activation config.yaml, état gateway). Cf. gateway_adapter.


class GatewayStatus(BaseModel):
    """État du gateway Hermes : tourne ou non, port de l'API server, présence de la clé API."""

    running: bool = False
    port: int = 8645
    api_key_present: bool = False


class MessagingEnvVar(BaseModel):
    """Un champ de configuration d'une plateforme (clé ``~/.hermes/.env``).

    ``redacted_value`` : aperçu masqué de la valeur enregistrée (jamais la valeur en clair).
    """

    key: str
    prompt: str
    description: str = ""
    required: bool = False
    is_password: bool = False
    advanced: bool = False
    is_set: bool = False
    redacted_value: str = ""


class MessagingPlatform(BaseModel):
    """Une plateforme de messagerie (Telegram, Discord, …) avec son état et son formulaire.

    - ``configured`` : toutes les clés requises sont présentes.
    - ``enabled`` : activée dans ``config.yaml`` (toggle).
    - ``state`` : ``disabled`` | ``needs_setup`` | ``ready`` | ``connected``.
    """

    id: str
    name: str
    emoji: str = ""
    description: str = ""
    docs_url: str = ""
    configured: bool = False
    enabled: bool = False
    state: str = "disabled"
    env_vars: list[MessagingEnvVar] = []
    # ``available`` : le canal est-il branchable dès maintenant ? ``False`` = affiché
    # mais grisé côté UI (ex. WhatsApp Cloud, en attente d'une configuration Meta).
    available: bool = True
    unavailable_reason: str = ""
    # ``recommended`` : mis en avant pour le client (badge « Recommandé », ex. Telegram).
    recommended: bool = False
    # ``expert_only`` : masqué au client, visible uniquement en Réglages avancés — mais
    # PLEINEMENT configurable (≠ ``available: False`` qui grise « Bientôt »). Pour les
    # canaux réservés aux techniciens (Signal, BlueBubbles : self-hébergement requis).
    expert_only: bool = False


class MessagingPlatformsResponse(BaseModel):
    platforms: list[MessagingPlatform]
    gateway_running: bool = False


# --- Onboarding Telegram « managed bot » (parcours QR 1-clic) ------------------
# Le client crée son bot en scannant un QR (feature Telegram Managed Bots via le
# service Nous), sans @BotFather ni copier-coller de token. Cf. gateway_adapter.


class TelegramPairingStart(BaseModel):
    """Pairing démarré : ce qu'on renvoie au front pour afficher le QR / le lien.

    Le ``poll_token`` (secret bearer) n'apparaît JAMAIS ici : il est conservé
    côté bridge et réinjecté au moment du poll.
    """

    pairing_id: str
    suggested_username: str = ""
    deep_link: str
    qr_payload: str
    expires_at: str | None = None


class TelegramPairingStatus(BaseModel):
    """État d'un pairing en cours. ``status`` : ``waiting`` | ``ready``.

    ``bot_username`` et ``owner_user_id`` ne sont renseignés qu'à l'état ``ready``.
    """

    status: str = "waiting"
    bot_username: str | None = None
    owner_user_id: int | None = None
    expires_at: str | None = None


class TelegramPairingApplyResult(BaseModel):
    """Résultat de l'application d'un pairing : token branché, canal activé,
    propriétaire auto-approuvé, home channel défini, gateway redémarré."""

    ok: bool = False
    platform: str = "telegram"
    bot_username: str | None = None
    owner_user_id: int | None = None
    needs_restart: bool = False
    restart_ok: bool = False
    restart_error: str | None = None
    error: str | None = None


class MessagingUser(BaseModel):
    """Un utilisateur d'une plateforme : autorisé (allowlist) ou en attente d'accès."""

    platform: str
    user_id: str
    user_name: str = ""
    approved_at: float | None = None
    pending_code: str | None = None
    age_minutes: float | None = None


class MessagingUsersResponse(BaseModel):
    """Liste des accès d'une plateforme : approuvés + demandes en attente."""

    approved: list[MessagingUser] = []
    pending: list[MessagingUser] = []


class MessagingActionResult(BaseModel):
    """Résultat générique d'une action plateforme (approuver / retirer / déconnecter)."""

    ok: bool = False
    needs_restart: bool = False
    restart_ok: bool = False
    restart_error: str | None = None
    error: str | None = None


class TelegramBotInfo(BaseModel):
    """Infos publiques du bot connecté (via getMe) — pour afficher/partager son lien.

    ``link`` = ``https://t.me/<username>`` : ce que le propriétaire partage pour
    inviter quelqu'un à écrire au bot.
    """

    username: str | None = None
    name: str | None = None
    link: str | None = None


# --- Onboarding Discord (parcours guidé : token → branché + invite 1-clic) -----
# Discord n'a pas de « managed bot » (contrairement à Telegram) : le client crée
# son app sur le portail développeur et colle le token. Le bridge valide le token,
# branche + active + redémarre, et génère l'URL d'invitation OAuth2 (« Ajouter à
# mon serveur ») pour que le client termine en 1 clic. Cf. gateway_adapter.


class DiscordApplyResult(BaseModel):
    """Résultat du branchement Discord : token validé, canal activé, gateway
    redémarré, + URL d'invitation à afficher pour ajouter le bot à un serveur.

    ``error`` est renseigné et ``ok`` reste ``False`` si le token est invalide
    (on ne dit jamais « connecté » sans avoir vérifié le token — honnêteté d'état).
    """

    ok: bool = False
    platform: str = "discord"
    bot_name: str | None = None
    invite_url: str | None = None
    needs_restart: bool = False
    restart_ok: bool = False
    restart_error: str | None = None
    error: str | None = None


class DiscordBotInfo(BaseModel):
    """Infos publiques du bot Discord connecté (via l'API Discord ``/users/@me``).

    ``invite_url`` = lien OAuth2 « Ajouter à mon serveur » (dérivé de l'application
    id du bot) : ce que le propriétaire clique pour installer le bot sur son serveur.
    """

    name: str | None = None
    application_id: str | None = None
    invite_url: str | None = None


# --- Onboarding Slack (parcours guidé : 2 tokens → branché) -------------------
# Slack n'a pas de « managed bot » : le client crée son app Slack et colle DEUX
# tokens — le bot token (xoxb-…, OAuth & Permissions) et le app-level token
# (xapp-…, Socket Mode). Le bridge valide les deux (auth.test + apps.connections.open),
# branche + active + redémarre. Pas d'URL d'invitation façon Discord : l'app est déjà
# installée dans le workspace quand on obtient le xoxb ; on affiche le workspace + bot.


class SlackApplyResult(BaseModel):
    """Résultat du branchement Slack : les 2 tokens validés, canal activé, gateway
    redémarré, + le nom du workspace et du bot à afficher.

    ``error`` est renseigné et ``ok`` reste ``False`` si un token est invalide
    (on ne dit jamais « connecté » sans avoir vérifié les tokens — honnêteté d'état).
    """

    ok: bool = False
    platform: str = "slack"
    bot_name: str | None = None
    team_name: str | None = None
    workspace_url: str | None = None
    needs_restart: bool = False
    restart_ok: bool = False
    restart_error: str | None = None
    error: str | None = None


class SlackBotInfo(BaseModel):
    """Infos publiques du bot Slack connecté (via l'API Slack ``auth.test``).

    ``workspace_url`` = URL du workspace où l'app est installée (ex.
    ``https://acme.slack.com/``), à afficher au propriétaire.
    """

    name: str | None = None
    team_name: str | None = None
    workspace_url: str | None = None


# --- Onboarding Email (validation réelle : login IMAP + SMTP → auto-activation) -
# Contrairement à un simple enregistrement, on TESTE vraiment la connexion (réception
# IMAP + envoi SMTP) avant de dire « connecté ». Si les deux passent : on enregistre,
# on active le canal tout seul et on redémarre — le client n'a aucun toggle à trouver.


class EmailApplyResult(BaseModel):
    """Résultat du branchement Email : identifiants testés en réel (IMAP + SMTP),
    canal activé automatiquement, gateway redémarré.

    ``error`` est renseigné et ``ok`` reste ``False`` si la connexion échoue
    (identifiants refusés, serveur injoignable) — on ne dit jamais « connecté »
    sans avoir prouvé la connexion (honnêteté d'état).
    """

    ok: bool = False
    platform: str = "email"
    address: str | None = None
    mailbox_count: int | None = None  # nb d'e-mails vus dans INBOX (preuve de connexion)
    needs_restart: bool = False
    restart_ok: bool = False
    restart_error: str | None = None
    error: str | None = None


# --- Kanban : tableau de tâches multi-agents (page « Tâches ») -----------------
# Source de vérité = Hermes (kanban.db, piloté par la CLI `hermes kanban --json`).
# Cf. kanban_adapter. Une tâche est assignée à un agent (profil) et passe par des statuts.


class KanbanBoard(BaseModel):
    """Un board Kanban (un par projet/flux de travail), avec compteurs par statut."""

    slug: str
    name: str
    description: str = ""
    icon: str = ""
    color: str = ""
    is_current: bool = False
    archived: bool = False
    total: int = 0
    counts: dict[str, int] = {}


class KanbanBoardsResponse(BaseModel):
    boards: list[KanbanBoard]
    current: str = "default"


class KanbanTask(BaseModel):
    """Une tâche du Kanban, assignée à un agent (profil) et exécutée dans un workspace isolé.

    ``status`` : triage | todo | ready | running | scheduled | blocked | review | done | archived.
    ``priority`` : entier (tiebreaker ; plus haut = plus prioritaire).
    """

    id: str
    title: str
    body: str | None = None
    assignee: str | None = None
    status: str = "todo"
    priority: int = 0
    tenant: str | None = None
    workspace_kind: str = "scratch"
    workspace_path: str | None = None
    branch_name: str | None = None
    created_by: str | None = None
    created_at: int | None = None
    started_at: int | None = None
    completed_at: int | None = None
    result: str | None = None
    skills: list[str] = []
    max_retries: int | None = None


class KanbanTasksResponse(BaseModel):
    tasks: list[KanbanTask]


# --- Intégrations (feature 004) ----------------------------------------------
# Skills connectables de Hermes exposées comme « intégrations » (Gmail, Notion, GitHub…).
# Source de vérité = catalogue curé (integrations_catalog) + état réel détecté côté Hermes
# (présence de clé dans ~/.hermes/.env, fichiers de token). Jamais de valeur de secret.
# Cf. specs/004-integrations.


class AuthMode(str, Enum):
    account = "account"  # connexion par compte (OAuth) — ex. Google, X
    key = "key"  # clé / token à saisir — ex. Notion, GitHub, Airtable
    credentials = "credentials"  # identifiants (IMAP/SMTP) — ex. Email
    path = "path"  # chemin d'un dossier local à indiquer — ex. Obsidian (coffre de notes)
    local = "local"  # sur l'appareil, sans secret — ex. Apple, Hue


class IntegrationStateEnum(str, Enum):
    not_connected = "not_connected"  # rien de configuré
    key_present = "key_present"  # clé posée mais accès non confirmé
    connected = "connected"  # accès réellement vérifié
    error = "error"  # configuration en erreur
    unavailable = "unavailable"  # skill absente / local non supporté ici


class Integration(BaseModel):
    """Une intégration connectable avec son état réel (jamais de valeur de secret)."""

    id: str
    auth_mode: AuthMode
    state: IntegrationStateEnum = IntegrationStateEnum.not_connected
    secret_state: SecretState | None = None  # pour le mode key uniquement (present/absent)
    subservices: list[str] = []
    authorized_services: list[str] | None = None  # pour Google si détectable
    visible: bool = True
    local_only: bool = False
    reason: str | None = None


class IntegrationsResponse(BaseModel):
    integrations: list[Integration]


# --- Mémoire / Second Cerveau (feature 005) ---------------------------------
# Le coffre = un dossier de fichiers .md (Obsidian). On expose une arborescence
# lisible, le contenu d'une note, et un statut honnête. Jamais de chemin absolu
# vers le client (uniquement des chemins relatifs au coffre).


class MemoryNode(BaseModel):
    """Un nœud de l'arborescence du coffre : un dossier (avec enfants) ou une note."""

    name: str  # nom affichable (sans extension pour une note)
    path: str  # chemin RELATIF au coffre (ex. "Clients/acme.md")
    type: Literal["folder", "note"]
    children: list["MemoryNode"] = []
    modified: float | None = None  # date de dernière modif (epoch, notes uniquement)


class MemoryTreeResponse(BaseModel):
    tree: list[MemoryNode]


class NoteContent(BaseModel):
    """Le contenu texte d'une note du coffre."""

    path: str  # chemin relatif au coffre
    content: str
    modified: float | None = None  # date de dernière modif (epoch)


class TrashItem(BaseModel):
    """Un élément de la corbeille du coffre (note ou dossier supprimé, récupérable)."""

    ref: str  # référence de corbeille (pour la restauration)
    path: str  # chemin d'origine (où l'élément sera restauré)
    name: str  # nom affichable
    type: Literal["folder", "note"]
    deleted_at: float  # date de suppression (epoch)
    size: int = 0  # octets occupés (le dirigeant voit la place récupérée avant de vider)


class TrashResponse(BaseModel):
    items: list[TrashItem]


class NoteWriteBody(BaseModel):
    """Corps de correction d'une note (lecture + correction par le patron).

    ``expected_modified`` (optionnel) porte la concurrence optimiste : le ``modified`` (mtime
    epoch) vu par l'appelant au dernier ``GET /memory/note`` pour ce chemin. Si fourni et qu'il ne
    correspond plus à l'état actuel du fichier (modifié depuis — voir
    ``memory_adapter.NoteConflict``), le serveur refuse l'écriture (409) plutôt que d'écraser la
    dernière version en silence. Omis = comportement rétro-compatible (aucune vérification), à ne
    PAS utiliser côté nouveau front qui a lu la note au préalable.
    """

    path: str
    content: str
    expected_modified: float | None = None


class NoteRenameBody(BaseModel):
    """Renommage d'une note (titre lisible, même dossier)."""

    path: str
    title: str


class NoteRestoreBody(BaseModel):
    """Restauration d'une note supprimée (annulation) depuis la corbeille."""

    trash_ref: str
    path: str


class FolderCreateBody(BaseModel):
    """Création d'un dossier dans le coffre (rangement manuel du dirigeant)."""

    parent: str = ""  # dossier parent relatif ("" = racine du coffre)
    name: str


class NoteMoveBody(BaseModel):
    """Déplacement d'une note vers un autre dossier du coffre."""

    path: str
    dest: str = ""  # dossier destination relatif ("" = racine)


class FolderRenameBody(BaseModel):
    """Renommage d'un dossier (non structurel)."""

    path: str
    name: str


class FolderMoveBody(BaseModel):
    """Déplacement d'un dossier (non structurel) vers un autre parent (« » = racine du coffre)."""

    path: str
    dest: str = ""  # dossier parent destination ("" = racine)


class FolderRestoreBody(BaseModel):
    """Restauration d'un dossier supprimé (annulation) depuis la corbeille."""

    trash_ref: str
    path: str


class MemoryStatus(BaseModel):
    """Statut honnête de la mémoire (jamais d'état non vérifié)."""

    ok: bool  # le coffre est accessible
    note_count: int  # nombre de notes présentes
    local_copy: bool = False  # une copie locale Obsidian est-elle reliée (sync Syncthing détectée)
    local_copy_synced_at: int | None = None  # epoch s. de la dernière sync locale, si connue
    sync_available: bool = False  # ce serveur PEUT-IL relier une copie locale (Syncthing provisionné)


class MemoryInitResponse(BaseModel):
    """Résultat de l'initialisation de la structure PARA du coffre."""

    created: list[str]  # dossiers/fichiers créés (vide si la structure existait déjà)


class InboxNoteBody(BaseModel):
    """Dépôt d'une note dans la Boîte de réception (zone d'écriture autonome de l'agent)."""

    title: str
    content: str


class ManagedNoteBody(BaseModel):
    """Écriture d'une note GÉRÉE : identifiée par ``note_id``, réécrite sur place à chaque rejeu."""

    note_id: str
    title: str
    content: str


# ── Recherche dans le coffre (spec 020) : recherche par mot ───────────────────


class SearchBody(BaseModel):
    """Requête de recherche par mot dans les notes du coffre."""

    query: str
    limit: int = 8


class SearchResult(BaseModel):
    """Un résultat de recherche : toujours un titre/chemin LISIBLE (jamais un ID technique)."""

    titre: str  # titre lisible de la note (pour citation)
    chemin: str  # chemin relatif au coffre (pour relecture via /memory/note)
    extrait: str  # passage pertinent
    score: float  # pertinence (plus haut = mieux)
    source_type: Literal["note", "document"] = "note"


class SearchResponse(BaseModel):
    """Réponse de /memory/search."""

    ok: bool
    query: str
    results: list[SearchResult] = []
    count: int


# ── Réglages du cerveau (feature 017) : Persona / Profil / Souvenirs ──────────


class PersonaContent(BaseModel):
    """Personnalité de l'assistant (SOUL.md), texte libre."""

    content: str


class PersonaWriteBody(BaseModel):
    """Corps d'écriture de la personnalité (sauvegarde explicite)."""

    content: str
    allow_empty: bool = False  # autorise explicitement l'écrasement par du vide


class ProfileContent(BaseModel):
    """Profil du dirigeant (USER.md) + compteurs (limite adoucie côté UI)."""

    content: str
    char_count: int
    char_limit: int


class ProfileWriteBody(BaseModel):
    """Corps d'écriture du profil du dirigeant."""

    content: str


class MemoryEntry(BaseModel):
    """Un souvenir (entrée de MEMORY.md), identifié par sa position."""

    index: int
    content: str


class MemoryEntriesResponse(BaseModel):
    """Liste des souvenirs + compteurs (limite totale adoucie côté UI)."""

    entries: list[MemoryEntry]
    char_count: int
    char_limit: int


class MemoryEntryBody(BaseModel):
    """Corps d'ajout/modification d'un souvenir.

    ``expected_content`` (optionnel) porte la concurrence optimiste : le contenu vu par
    l'appelant au dernier ``GET /memory/entries`` pour cet index. Si fourni et qu'il ne
    correspond plus au contenu actuel de l'entrée visée (l'index a dérivé — voir
    ``brain_adapter.EntryConflictError``), le serveur refuse l'écriture (409) plutôt que
    d'écraser une autre entrée que celle affichée. Omis = comportement rétro-compatible
    (aucune vérification), à ne PAS utiliser côté nouveau front.
    """

    content: str
    expected_content: str | None = None
