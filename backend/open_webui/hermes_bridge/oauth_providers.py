"""Registre des fournisseurs OAuth supportés par le moteur centralisé d'Agent OS.

Chaque entrée décrit statiquement un fournisseur : URLs du flow, scopes requis, noms
des variables d'environnement portant les credentials CENTRALISÉS (provisionnés une
fois côté serveur, jamais transmis au client), et nom du fichier token attestant la
connexion.

Convention de stockage :
- tokens : ``HERMES_HOME / token_file``   (présence = connecté, cf. honnetete-libelles-etat-ui)
- pending : ``HERMES_HOME / "oauth-pending" / f"{provider_id}.json"``  (temporaire, PKCE)

Cf. specs/016-oauth-un-clic/spec.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OAuthProviderDef:
    """Définition statique immuable d'un fournisseur OAuth centralisé.

    Attributs
    ---------
    id:
        Identifiant unique (ex. "microsoft-365").
    auth_url:
        Endpoint d'autorisation chez le fournisseur.
    token_url:
        Endpoint d'échange code/token chez le fournisseur.
    scopes:
        Scopes OAuth délégués demandés (tuple immuable).
    client_id_env:
        Nom de la variable d'environnement portant le ``client_id`` centralisé.
    client_secret_env:
        Nom de la variable d'environnement portant le ``client_secret`` centralisé.
    token_file:
        Nom du fichier token stocké dans ``HERMES_HOME`` (présence atteste la connexion).
    use_pkce:
        Si ``True``, le flow utilise PKCE S256 (recommandé pour tous les fournisseurs modernes).
    env_key:
        Variable dans ``~/.hermes/.env`` où écrire l'``access_token`` après l'échange.
        ``None`` (défaut) = pas d'écriture dans .env (cas Microsoft 365).
        Permet aux skills Hermes existantes de lire le token sans aucune modification.
    token_auth:
        Mode d'authentification lors du POST sur ``token_url``.
        ``"body"`` (défaut) : ``client_id`` et ``client_secret`` dans le corps du POST.
        ``"basic"`` : HTTP Basic Authentication ``client_id:client_secret`` dans l'en-tête
        (requis par Notion, cf. https://developers.notion.com/docs/authorization).
    """

    id: str
    auth_url: str
    token_url: str
    scopes: tuple[str, ...]
    client_id_env: str
    client_secret_env: str
    token_file: str
    use_pkce: bool = True
    env_key: str | None = None
    token_auth: str = "body"
    extra_auth_params: tuple[tuple[str, str], ...] = ()
    """Paramètres supplémentaires à ajouter à l'URL d'autorisation.

    Chaque élément est un couple ``(nom, valeur)`` injecté tel quel dans les
    query-params de la requête d'autorisation.  Exemples :
    - Microsoft 365 : ``(("prompt", "consent"),)``
    - Dropbox : ``(("token_access_type", "offline"),)``
    """
    token_format: str = "raw"
    """Format de stockage du token après l'échange ou le renouvellement.

    ``"raw"`` (défaut) : la réponse brute du fournisseur est stockée telle quelle
    dans ``token_file``. Comportement inchangé pour Microsoft 365 et toutes les apps
    sans skill Hermes existante.

    ``"google_authorized_user"`` : la réponse brute est transformée vers le format
    ``authorized_user`` attendu par ``google.oauth2.credentials.Credentials.from_authorized_user_file()``.
    Indispensable pour que la skill Google de Hermes lise ``google_token.json`` sans
    aucune modification du moteur ou du ``setup.py`` Google.
    """
    client_id_param: str = "client_id"
    """Nom du paramètre portant le ``client_id`` dans les requêtes OAuth.

    Défaut ``"client_id"`` (standard OAuth2). TikTok déroge : il attend ``"client_key"``
    à la fois dans l'URL d'autorisation et dans l'échange de token. Utilisé par
    ``build_auth_url`` et ``exchange_code`` (mode ``body``) du moteur.
    """
    long_lived_exchange: bool = False
    """Si ``True``, échange le token court après l'``authorization_code`` contre un token
    longue durée avant stockage (spécifique Meta : ``grant_type=fb_exchange_token`` → ~60 j).
    Défaut ``False`` (aucun second échange). Utilisé par ``exchange_code``.
    """
    revoke_url: str = ""
    """Endpoint de révocation du token chez le fournisseur (best-effort à la déconnexion).

    ``""`` (défaut) : ``disconnect()`` supprime seulement le token local. Si renseigné,
    ``disconnect()`` POST le token sur cette URL AVANT la suppression locale, afin que
    « Déconnecter » révoque réellement l'accès côté fournisseur (cf. honnetete-libelles-etat-ui).
    L'appel est best-effort : une erreur réseau n'empêche jamais la déconnexion locale.
    Exemple Google : ``https://oauth2.googleapis.com/revoke`` (révoque tout le grant via le refresh_token).
    """
    client_secret_file: str | None = None
    """Nom d'un fichier ``client_secret`` à écrire dans ``HERMES_HOME`` en plus du token.

    ``None`` (défaut) : aucun fichier supplémentaire (cas général).

    Certaines skills Hermes exigent, en plus du token, un fichier d'identifiants client au
    format Google Cloud (clé ``"web"`` : ``client_id``/``client_secret``/``auth_uri``/``token_uri``).
    C'est le cas de la skill ``google-workspace`` qui déclare ``google_client_secret.json``
    dans ses ``required_credential_files`` : sans ce fichier, la skill est marquée « non
    configurée » même quand le token suffit fonctionnellement (backend ``gws``). Le moteur
    reconstruit ce fichier à partir des identifiants OAuth centralisés (mêmes valeurs que
    celles déjà présentes dans le token), en 0600, sans jamais modifier la skill Hermes.
    """


# ---------------------------------------------------------------------------
# Registre v1 — fournisseurs centralisés
# ---------------------------------------------------------------------------

REGISTRY: tuple[OAuthProviderDef, ...] = (
    OAuthProviderDef(
        id="microsoft-365",
        auth_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        scopes=(
            "User.Read",
            "Mail.ReadWrite",
            "Mail.Send",
            "Calendars.ReadWrite",
            "Contacts.ReadWrite",
            "Files.ReadWrite.All",
            "offline_access",
        ),
        client_id_env="AGENTOS_MS365_CLIENT_ID",
        client_secret_env="AGENTOS_MS365_CLIENT_SECRET",
        token_file="microsoft_token.json",
        use_pkce=True,
        # env_key absent : Microsoft ne pilote pas une skill Hermes via Bearer .env
        # token_auth "body" : Microsoft accepte les credentials dans le corps du POST
        # prompt=consent : garantit le consentement explicite à la première autorisation
        extra_auth_params=(("prompt", "consent"),),
    ),
    OAuthProviderDef(
        id="notion",
        # Notion OAuth — l'app Notion définit ses capacités à la création ;
        # aucun scope n'est passé dans l'URL d'autorisation.
        auth_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        scopes=(),
        client_id_env="AGENTOS_NOTION_CLIENT_ID",
        client_secret_env="AGENTOS_NOTION_CLIENT_SECRET",
        token_file="notion_token.json",
        # Notion n'implémente pas PKCE ; PKCE désactivé.
        use_pkce=False,
        # L'access_token Notion est un Bearer utilisable directement par la skill Hermes.
        env_key="NOTION_API_KEY",
        # Notion EXIGE HTTP Basic auth pour l'échange de code (cf. doc officielle).
        token_auth="basic",
    ),
    OAuthProviderDef(
        id="github",
        auth_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scopes=("repo", "read:org", "workflow"),
        client_id_env="AGENTOS_GITHUB_CLIENT_ID",
        client_secret_env="AGENTOS_GITHUB_CLIENT_SECRET",
        token_file="github_token.json",
        # GitHub OAuth classique n'utilise pas PKCE.
        use_pkce=False,
        # L'access_token GitHub est utilisable comme Bearer par la skill Hermes.
        env_key="GITHUB_TOKEN",
        # GitHub accepte les credentials dans le corps du POST.
        token_auth="body",
    ),
    OAuthProviderDef(
        id="airtable",
        auth_url="https://airtable.com/oauth2/v1/authorize",
        token_url="https://airtable.com/oauth2/v1/token",
        scopes=("data.records:read", "data.records:write", "schema.bases:read"),
        client_id_env="AGENTOS_AIRTABLE_CLIENT_ID",
        client_secret_env="AGENTOS_AIRTABLE_CLIENT_SECRET",
        token_file="airtable_token.json",
        # Airtable EXIGE PKCE S256 (cf. https://airtable.com/developers/web/api/oauth-reference).
        use_pkce=True,
        # L'access_token Airtable est utilisable comme Bearer par la skill Hermes.
        env_key="AIRTABLE_API_KEY",
        # Airtable accepte les credentials dans le corps du POST.
        token_auth="body",
    ),
    # ------------------------------------------------------------------
    # Nouvelles intégrations OAuth « 1 clic » (apps sans skill Hermes existante)
    # env_key=None : le token brut est stocké dans token_file, aucune écriture dans .env
    # ------------------------------------------------------------------
    OAuthProviderDef(
        id="calendly",
        auth_url="https://auth.calendly.com/oauth/authorize",
        token_url="https://auth.calendly.com/oauth/token",
        # Calendly n'exige pas de scopes dans l'URL d'autorisation (périmètre défini
        # lors de la création de l'app Calendly dans le Developer Portal).
        scopes=(),
        client_id_env="AGENTOS_CALENDLY_CLIENT_ID",
        client_secret_env="AGENTOS_CALENDLY_CLIENT_SECRET",
        token_file="calendly_token.json",
        # Calendly supporte PKCE S256.
        use_pkce=True,
        # Pas de skill Hermes existante : token brut stocké seulement dans token_file.
        env_key=None,
        token_auth="body",
    ),
    OAuthProviderDef(
        id="box",
        auth_url="https://account.box.com/api/oauth2/authorize",
        token_url="https://api.box.com/oauth2/token",
        # Box gère les périmètres via les scopes configurés dans la Box App Console ;
        # aucun scope n'est requis dans l'URL d'autorisation pour le flow standard.
        scopes=(),
        client_id_env="AGENTOS_BOX_CLIENT_ID",
        client_secret_env="AGENTOS_BOX_CLIENT_SECRET",
        token_file="box_token.json",
        # Box classique n'utilise pas PKCE.
        use_pkce=False,
        # Pas de skill Hermes existante : token brut stocké seulement dans token_file.
        env_key=None,
        token_auth="body",
    ),
    OAuthProviderDef(
        id="dropbox",
        auth_url="https://www.dropbox.com/oauth2/authorize",
        token_url="https://api.dropboxapi.com/oauth2/token",
        # Dropbox gère les périmètres via les permissions configurées dans l'app Dropbox.
        scopes=(),
        client_id_env="AGENTOS_DROPBOX_CLIENT_ID",
        client_secret_env="AGENTOS_DROPBOX_CLIENT_SECRET",
        token_file="dropbox_token.json",
        # Dropbox supporte PKCE S256.
        use_pkce=True,
        # Pas de skill Hermes existante : token brut stocké seulement dans token_file.
        env_key=None,
        token_auth="body",
        # INDISPENSABLE : sans token_access_type=offline, Dropbox ne délivre PAS de
        # refresh_token (uniquement un access_token à courte durée de vie).
        extra_auth_params=(("token_access_type", "offline"),),
    ),
    OAuthProviderDef(
        id="salesforce",
        auth_url="https://login.salesforce.com/services/oauth2/authorize",
        token_url="https://login.salesforce.com/services/oauth2/token",
        # api : accès API REST ; refresh_token : obtenir un refresh token de longue durée.
        scopes=("api", "refresh_token"),
        client_id_env="AGENTOS_SALESFORCE_CLIENT_ID",
        client_secret_env="AGENTOS_SALESFORCE_CLIENT_SECRET",
        token_file="salesforce_token.json",
        # Salesforce supporte PKCE S256 depuis l'API v50+.
        use_pkce=True,
        # Pas de skill Hermes existante : token brut stocké seulement dans token_file.
        env_key=None,
        token_auth="body",
    ),
    OAuthProviderDef(
        id="clickup",
        auth_url="https://app.clickup.com/api",
        token_url="https://api.clickup.com/api/v2/oauth/token",
        # ClickUp ne définit pas de scopes dans l'URL d'autorisation.
        scopes=(),
        client_id_env="AGENTOS_CLICKUP_CLIENT_ID",
        client_secret_env="AGENTOS_CLICKUP_CLIENT_SECRET",
        token_file="clickup_token.json",
        # ClickUp n'implémente pas PKCE.
        use_pkce=False,
        # Pas de skill Hermes existante : token brut stocké seulement dans token_file.
        env_key=None,
        # NOTE ClickUp : la doc officielle (POST /api/v2/oauth/token) ne documente que
        # client_id, client_secret et code ; elle ne mentionne pas grant_type. Le moteur
        # générique (_post_token_request) envoie néanmoins grant_type="authorization_code"
        # comme pour tous les autres fournisseurs. Comportement actuel figé et vérifié
        # par test_exchange_code_clickup_* (test_oauth_engine.py) : le champ additionnel
        # est envoyé, pas de PKCE, credentials dans le corps du POST (token_auth="body").
        # Pas encore validé contre l'API réelle de ClickUp — à revoir si l'échange
        # échoue en production (ClickUp pourrait rejeter un champ non reconnu).
        token_auth="body",
    ),
    # ------------------------------------------------------------------
    # Google Workspace — intégration OAuth centralisée « 1 clic »
    # La skill Hermes lit HERMES_HOME/google_token.json via
    # google.oauth2.credentials.Credentials.from_authorized_user_file().
    # Ce format exige un dict "authorized_user" strict (type, client_id, client_secret,
    # refresh_token, token, token_uri, scopes) — d'où token_format="google_authorized_user".
    # Le moteur transforme la réponse brute avant d'écrire google_token.json.
    # ------------------------------------------------------------------
    OAuthProviderDef(
        id="google-workspace",
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=(
            "openid",
            "email",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/contacts",
            # Services additionnels pilotés côté bridge (Chemin A, google_direct.py) :
            "https://www.googleapis.com/auth/presentations",  # Google Slides
            "https://www.googleapis.com/auth/analytics.readonly",  # Google Analytics (GA4)
            "https://www.googleapis.com/auth/webmasters.readonly",  # Search Console
        ),
        client_id_env="AGENTOS_GOOGLE_CLIENT_ID",
        client_secret_env="AGENTOS_GOOGLE_CLIENT_SECRET",
        token_file="google_token.json",
        # PKCE S256 recommandé par Google pour les apps installées et les web apps
        # qui gèrent elles-mêmes le flow OAuth (pas d'implicit flow).
        use_pkce=True,
        # env_key absent : la skill Hermes lit directement google_token.json via
        # google-auth, pas via ~/.hermes/.env.
        env_key=None,
        token_auth="body",
        # access_type=offline : indispensable pour obtenir un refresh_token Google
        # (sans cela, Google ne délivre qu'un access_token à courte durée de vie).
        # prompt=consent : force le re-consentement afin de garantir l'émission d'un
        # refresh_token même si l'utilisateur a déjà autorisé l'app.
        extra_auth_params=(
            ("access_type", "offline"),
            ("prompt", "consent"),
        ),
        # Transformation vers le format "authorized_user" attendu par google-auth.
        token_format="google_authorized_user",
        # La skill google-workspace exige aussi google_client_secret.json (required_credential_files) :
        # le moteur le reconstruit depuis les identifiants centralisés, sinon skill « non configurée ».
        client_secret_file="google_client_secret.json",
        # Révocation réelle côté Google à la déconnexion (honnêteté d'état) : POST du
        # refresh_token sur cet endpoint révoque l'ensemble de l'autorisation.
        revoke_url="https://oauth2.googleapis.com/revoke",
    ),
    # ------------------------------------------------------------------
    # Réseaux sociaux — publication souveraine (skills social-media/<reseau>)
    # L'access_token est recopié dans ~/.hermes/.env via env_key ; la skill Hermes
    # correspondante le lit comme Bearer pour publier (aucune modif moteur).
    # ------------------------------------------------------------------
    OAuthProviderDef(
        id="linkedin",
        auth_url="https://www.linkedin.com/oauth/v2/authorization",
        token_url="https://www.linkedin.com/oauth/v2/accessToken",
        # openid + profile : identité (récupérer l'URN de l'auteur via /v2/userinfo).
        # email : adresse (facultatif mais courant). w_member_social : PUBLIER au nom du membre.
        scopes=("openid", "profile", "email", "w_member_social"),
        client_id_env="AGENTOS_LINKEDIN_CLIENT_ID",
        client_secret_env="AGENTOS_LINKEDIN_CLIENT_SECRET",
        token_file="linkedin_token.json",
        # LinkedIn = OAuth2 authorization-code classique (pas de PKCE), credentials dans
        # le corps du POST (cf. audit Postiz : POST sur /oauth/v2/accessToken avec
        # client_id + client_secret en x-www-form-urlencoded).
        use_pkce=False,
        # L'access_token LinkedIn est un Bearer utilisable directement par la skill Hermes.
        env_key="LINKEDIN_ACCESS_TOKEN",
        token_auth="body",
    ),
    OAuthProviderDef(
        id="tiktok",
        auth_url="https://www.tiktok.com/v2/auth/authorize/",
        token_url="https://open.tiktokapis.com/v2/oauth/token/",
        # user.info.basic : identité (open_id). video.publish + video.upload : publier.
        scopes=("user.info.basic", "video.publish", "video.upload"),
        client_id_env="AGENTOS_TIKTOK_CLIENT_ID",
        client_secret_env="AGENTOS_TIKTOK_CLIENT_SECRET",
        token_file="tiktok_token.json",
        # TikTok EXIGE PKCE S256 (code_verifier envoyé à l'échange de token).
        use_pkce=True,
        # L'access_token TikTok est un Bearer utilisable directement par la skill Hermes.
        env_key="TIKTOK_ACCESS_TOKEN",
        token_auth="body",
        # TikTok déroge à OAuth2 : le paramètre du client s'appelle "client_key"
        # (pas "client_id"), dans l'URL d'autorisation ET dans l'échange de token.
        client_id_param="client_key",
    ),
    OAuthProviderDef(
        id="meta",
        auth_url="https://www.facebook.com/v20.0/dialog/oauth",
        token_url="https://graph.facebook.com/v20.0/oauth/access_token",
        # Un seul OAuth Meta couvre Facebook (Pages) ET Instagram (comptes pro).
        # pages_manage_posts : publier sur une Page. instagram_content_publish : publier sur IG.
        scopes=(
            "public_profile",
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
            "instagram_basic",
            "instagram_content_publish",
            "business_management",
        ),
        client_id_env="AGENTOS_META_CLIENT_ID",
        client_secret_env="AGENTOS_META_CLIENT_SECRET",
        token_file="meta_token.json",
        # Meta n'utilise pas PKCE (flow serveur classique).
        use_pkce=False,
        # L'access_token Meta (long-lived) pilote la skill de publication FB/IG.
        env_key="META_ACCESS_TOKEN",
        token_auth="body",
        # Meta délivre d'abord un token court → on l'échange contre un token ~60 j.
        long_lived_exchange=True,
    ),
)


def by_id(provider_id: str) -> OAuthProviderDef | None:
    """Retourne la définition d'un fournisseur OAuth par son identifiant, ou ``None``."""
    for entry in REGISTRY:
        if entry.id == provider_id:
            return entry
    return None
