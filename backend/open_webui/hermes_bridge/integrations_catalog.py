"""Catalogue curé des intégrations connectables d'Agent OS (page Capacités, onglet Intégrations).

Source de vérité du « quoi » : quelles skills natives de Hermes sont exposées comme
intégrations connectables, leur mode d'auth et comment détecter leur état. Le « comment c'est
présenté » (nom FR, description, logo) vit côté front (integrationLabels.ts / integrationLogos.ts).

Cf. specs/004-integrations/ (data-model.md, research.md).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationDef:
    """Définition statique d'une intégration connectable.

    - ``auth_mode`` : account (OAuth) · key (clé/token) · credentials (IMAP) · local (sur l'appareil).
    - ``secret_env`` : variable d'env attendue dans ~/.hermes/.env (mode ``key`` uniquement).
    - ``state_file`` : fichier dont la présence atteste d'une connexion (modes account/credentials),
      relatif à HERMES_HOME si ``state_file_home`` est False, sinon relatif au HOME utilisateur.
    """

    id: str
    skill: str
    auth_mode: str
    subservices: tuple[str, ...]
    secret_env: str | None = None
    state_file: str | None = None
    state_file_home: bool = False  # True => chemin relatif au HOME utilisateur (~), pas à HERMES_HOME
    default_visible: bool = True
    local_only: bool = False


# Catalogue v1 — l'ordre détermine l'affichage.
CATALOG: tuple[IntegrationDef, ...] = (
    IntegrationDef(
        id="google-workspace",
        skill="productivity/google-workspace",
        auth_mode="account",
        # Carte Google UNIFIÉE : tous les services Google s'activent avec le même compte
        # (un seul google_token.json), on ne montre donc qu'UNE carte au client. Les tags de
        # la carte restent courts (3 services phares) comme les autres intégrations ; la liste
        # complète (Gmail, Agenda, Drive, Sheets, Docs, Contacts, Meet, Slides, Analytics,
        # Search Console) est détaillée dans la modale « Voir ce que ça fait » côté front.
        subservices=("Gmail", "Agenda", "Drive"),
        state_file="google_token.json",  # relatif à HERMES_HOME
        default_visible=True,
    ),
    IntegrationDef(
        id="microsoft-365",
        skill="productivity/microsoft-365",
        auth_mode="account",
        # Tags courts (3 services phares) comme les autres cartes ; la liste complète
        # (Outlook, Agenda, OneDrive, Word, Excel, PowerPoint, Teams, OneNote, To Do, Contacts)
        # est détaillée dans la modale « Voir ce que ça fait » côté front.
        subservices=("Outlook", "Teams", "OneDrive"),
        state_file="microsoft_token.json",  # produit par le moteur OAuth 1 clic (feature 016)
        default_visible=True,
    ),
    # Note : Meet, Slides, Analytics et Search Console ne sont PLUS des cartes séparées.
    # Ils s'activent avec le même compte Google et sont désormais listés comme sous-services
    # de « google-workspace » ci-dessus (carte unifiée). Les capacités restent pilotées par
    # google_direct.py (Chemin A) — seul l'affichage change, aucune fonction perdue.
    IntegrationDef(
        id="notion",
        skill="productivity/notion",
        auth_mode="key",
        subservices=("Pages", "Bases de données", "Recherche"),
        secret_env="NOTION_API_KEY",
        default_visible=True,
    ),
    IntegrationDef(
        id="github",
        skill="github",
        auth_mode="key",
        subservices=("Dépôts", "Issues", "Pull requests"),
        secret_env="GITHUB_TOKEN",
        default_visible=True,
    ),
    IntegrationDef(
        id="airtable",
        skill="productivity/airtable",
        auth_mode="key",
        subservices=("Bases", "Tables", "Enregistrements"),
        secret_env="AIRTABLE_API_KEY",
        default_visible=True,
    ),
    IntegrationDef(
        id="email",
        skill="email/himalaya",
        auth_mode="credentials",
        subservices=("Réception", "Envoi", "Recherche"),
        state_file=".config/himalaya/config.toml",
        state_file_home=True,
        default_visible=True,
    ),
    IntegrationDef(
        id="obsidian",
        skill="note-taking/obsidian",
        auth_mode="path",
        subservices=("Notes", "Recherche", "Liens"),
        secret_env="OBSIDIAN_VAULT_PATH",  # chemin du coffre (pas un secret), dans ~/.hermes/.env
        default_visible=True,
    ),
    IntegrationDef(
        id="x",
        skill="social-media/xurl",
        auth_mode="account",
        subservices=("Posts", "Recherche", "Messages"),
        state_file=".xurl",
        state_file_home=True,
        default_visible=False,
    ),
    IntegrationDef(
        id="apple",
        skill="apple",
        auth_mode="local",
        subservices=("Notes", "Rappels", "iMessage"),
        default_visible=False,
        local_only=True,
    ),
    IntegrationDef(
        id="hue",
        skill="smart-home/openhue",
        auth_mode="local",
        subservices=("Lampes", "Scènes"),
        default_visible=False,
        local_only=True,
    ),
    # ------------------------------------------------------------------
    # Nouvelles intégrations OAuth « 1 clic » (apps sans skill Hermes existante)
    # state_file : nom du fichier token produit par le moteur OAuth (feature 016)
    # ------------------------------------------------------------------
    IntegrationDef(
        id="calendly",
        skill="scheduling/calendly",
        auth_mode="account",
        subservices=("Rendez-vous", "Disponibilités", "Événements"),
        state_file="calendly_token.json",
        default_visible=True,
    ),
    # Cal.com : alternative open source à Calendly. Connexion par CLÉ API (self-service,
    # « cal_live_… » depuis Paramètres → Sécurité → API keys). Testée en réel via /v1/me.
    IntegrationDef(
        id="cal-com",
        skill="scheduling/cal-com",
        auth_mode="key",
        subservices=("Rendez-vous", "Disponibilités", "Réservations"),
        secret_env="CALCOM_API_KEY",
        default_visible=True,
    ),
    IntegrationDef(
        id="box",
        skill="storage/box",
        auth_mode="account",
        subservices=("Fichiers", "Dossiers", "Partage"),
        state_file="box_token.json",
        default_visible=True,
    ),
    IntegrationDef(
        id="dropbox",
        skill="storage/dropbox",
        auth_mode="account",
        subservices=("Fichiers", "Dossiers", "Partage"),
        state_file="dropbox_token.json",
        default_visible=True,
    ),
    IntegrationDef(
        id="salesforce",
        skill="crm/salesforce",
        auth_mode="account",
        subservices=("Contacts", "Opportunités", "Comptes"),
        state_file="salesforce_token.json",
        default_visible=True,
    ),
    IntegrationDef(
        id="clickup",
        skill="project-management/clickup",
        auth_mode="account",
        subservices=("Tâches", "Projets", "Listes"),
        state_file="clickup_token.json",
        default_visible=True,
    ),
    # ------------------------------------------------------------------
    # Réseaux sociaux — connexion 1 clic (moteur OAuth 016) + skill de publication
    # souveraine (social-media/<reseau>). state_file = token produit par le moteur.
    # ------------------------------------------------------------------
    IntegrationDef(
        id="linkedin",
        skill="social-media/linkedin",
        auth_mode="account",
        subservices=("Publier des posts", "Publier au nom du membre"),
        state_file="linkedin_token.json",
        default_visible=True,
    ),
    IntegrationDef(
        id="tiktok",
        skill="social-media/tiktok",
        auth_mode="account",
        subservices=("Publier des vidéos",),
        state_file="tiktok_token.json",
        default_visible=True,
    ),
    # Facebook + Instagram partagent UN SEUL OAuth Meta (un seul meta_token.json),
    # comme les services Google partagent google_token.json. Présentés séparément.
    IntegrationDef(
        id="facebook",
        skill="social-media/meta",
        auth_mode="account",
        subservices=("Publier sur une Page",),
        state_file="meta_token.json",
        default_visible=True,
    ),
    IntegrationDef(
        id="instagram",
        skill="social-media/meta",
        auth_mode="account",
        subservices=("Publier une photo", "Publier une vidéo"),
        state_file="meta_token.json",
        default_visible=True,
    ),
)


def by_id(integration_id: str) -> IntegrationDef | None:
    """Retourne la définition d'une intégration par son id, ou None."""
    for entry in CATALOG:
        if entry.id == integration_id:
            return entry
    return None
