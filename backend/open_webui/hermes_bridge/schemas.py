"""Modèles Pydantic des corps de requête du bridge.

Extraits de main.py (P8) et regroupés en un seul endroit, importés par les routers.
"""

from __future__ import annotations

from pydantic import BaseModel


class CredentialBody(BaseModel):
    value: str


class GoogleClientSecretBody(BaseModel):
    client_secret_json: dict


class GoogleAuthCodeBody(BaseModel):
    code: str


class OAuthExchangeBody(BaseModel):
    """Corps de l'échange OAuth « 1 clic » : code + state reçus au retour de redirection."""

    code: str
    state: str


class EmailGuessBody(BaseModel):
    email: str


class EmailCredentialsBody(BaseModel):
    email: str
    password: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int


class AwsCredentialBody(BaseModel):
    access_key_id: str
    secret_access_key: str
    region: str | None = None


class AgentCreateBody(BaseModel):
    name: str
    description: str = ""
    soul: str = ""
    avatar: str | None = None


class AgentActiveBody(BaseModel):
    name: str


class SoulBody(BaseModel):
    content: str


class AvatarBody(BaseModel):
    """Nom de fichier (ou chemin relatif) de l'avatar d'un agent. ``None`` = désélection."""

    avatar: str | None = None


class CustomSkillCreateBody(BaseModel):
    """Création d'une compétence maison : nom + à quoi ça sert + comment faire + catégorie."""

    label: str
    description: str = ""
    instructions: str = ""
    category: str = "Autres"


class DescriptionBody(BaseModel):
    description: str


class ToggleToolBody(BaseModel):
    """Active/désactive un outil (compétence ou MCP) pour un agent donné."""

    name: str
    enabled: bool


class MessagingUpdateBody(BaseModel):
    env: dict[str, str] | None = None
    clear_env: list[str] | None = None
    enabled: bool | None = None


class MessagingApproveBody(BaseModel):
    """Autorise un utilisateur : soit via un code en attente (``code``), soit
    directement par son identifiant (``user_id``, ex. auto-approbation)."""

    code: str | None = None
    user_id: str | None = None
    user_name: str = ""


class DiscordApplyBody(BaseModel):
    """Branchement Discord : le token du bot collé depuis le portail développeur."""

    token: str


class SlackApplyBody(BaseModel):
    """Branchement Slack : les deux tokens collés depuis le tableau de bord Slack —
    le bot token (``xoxb-…``, OAuth & Permissions) et le app-level token
    (``xapp-…``, Socket Mode, scope ``connections:write``)."""

    bot_token: str
    app_token: str


class EmailApplyBody(BaseModel):
    """Branchement Email : adresse + mot de passe (d'application pour Gmail/Outlook) +
    serveurs IMAP/SMTP (auto-détectés côté front depuis le domaine)."""

    address: str
    password: str
    imap_host: str
    smtp_host: str


class KanbanBoardCreateBody(BaseModel):
    slug: str
    name: str | None = None


class KanbanTaskCreateBody(BaseModel):
    title: str
    body: str | None = None
    assignee: str | None = None
    priority: int | None = None
    workspace: str | None = None
    triage: bool = False
    board: str | None = None


class KanbanActionBody(BaseModel):
    board: str | None = None
    reason: str | None = None
    result: str | None = None
    assignee: str | None = None


class McpKeyBody(BaseModel):
    value: str


class McpConnectorCreate(BaseModel):
    from_catalog: str | None = None
    # Installation depuis le registre distant (résolution du manifest côté bridge).
    from_registry: str | None = None
    fields: dict | None = None  # valeurs des champs de config (MCP stdio à clé)
    # Connecteur custom (US5)
    name: str | None = None
    transport: str | None = None
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    auth_type: str | None = None


class McpEnabledBody(BaseModel):
    enabled: bool


class CapabilityEnabledBody(BaseModel):
    enabled: bool


class ToolKeyBody(BaseModel):
    values: dict[str, str]


class ToolDisconnectBody(BaseModel):
    keys: list[str]


class ToolProviderBody(BaseModel):
    slug: str


# --- Automatisations (feature 013) -------------------------------------------


class Rhythm(BaseModel):
    """Rythme d'une automatisation, exprimé en preset simple côté dirigeant.

    type ∈ {daily, weekly, interval, once, advanced}. Le bridge le traduit en
    ``schedule`` Hermes (cf. automations_adapter.rhythm_to_schedule).
    """

    type: str
    time: str | None = None  # daily/weekly : "HH:MM"
    weekday: int | None = None  # weekly : 0=lundi .. 6=dimanche
    every_minutes: int | None = None  # interval
    at: str | None = None  # once : timestamp ISO
    schedule: str | None = None  # advanced (Mode Expert) : expression brute


class AutomationCreate(BaseModel):
    name: str
    instruction: str | None = None  # requis sauf si skills fourni (parité Hermes)
    rhythm: Rhythm
    skills: list[str] | None = None  # Mode Expert
    deliver: str | None = None  # Mode Expert


class AutomationUpdate(BaseModel):
    name: str | None = None
    instruction: str | None = None
    rhythm: Rhythm | None = None
    skills: list[str] | None = None
    deliver: str | None = None
    status: str | None = None  # "active" | "paused"


# --- Calendrier (feature 014) ------------------------------------------------


class EventCreate(BaseModel):
    title: str
    start: str  # ISO 8601 (heure locale, sans fuseau ; fuseau porté par ``tz``)
    end: str  # ISO 8601 (heure locale, sans fuseau)
    location: str | None = None
    description: str | None = None
    with_meet: bool = False  # ajoute un lien Google Meet (réunion vidéo, Google seul)
    source: str | None = None  # google | outlook | calendly (None = 1re source connectée)
    tz: str = "UTC"  # fuseau IANA du client (ex. « Europe/Paris »), pour Outlook


class SlidesCreate(BaseModel):
    title: str
    slides: list[str] | None = None  # plan : une diapo par ligne (optionnel)
