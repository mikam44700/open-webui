"""Traduction des étapes de travail de l'agent (event SSE « hermes.tool.progress ») en
phrases françaises lisibles pour un dirigeant non-tech.

Le moteur Hermes envoie {tool, emoji, label} où :
  - `tool`  = nom technique de l'outil (ex. « browser_navigate »),
  - `label` = argument brut (URL, requête, chemin, commande… selon l'outil).

On produit une phrase du style « 🌐 Je consulte techcrunch.com » au lieu d'afficher
« browser_navigate » ou une URL complète. La clé de traduction est `tool` (déterministe) ;
`label` n'est inséré comme contexte que lorsqu'il est lisible (domaine d'une URL, requête).

Garde-fous :
  - un outil inconnu tombe sur un repli de FAMILLE (préfixe : browser_/web_/kanban_/…),
    puis sur un repli générique « ⚙️ Je travaille sur ta demande » — JAMAIS le nom technique.
  - le contexte est nettoyé (URL → domaine sans www, texte tronqué, une seule ligne).
"""

from __future__ import annotations

from urllib.parse import urlparse

# tool → (emoji, gabarit). « {ctx} » est remplacé par le contexte nettoyé (domaine/requête).
# Un gabarit SANS « {ctx} » est une phrase complète (on n'expose pas l'argument technique,
# ex. la « ref » d'un clic ou une commande shell).
_TOOL_TEMPLATES: dict[str, tuple[str, str]] = {
    # Recherche & web
    "web_search": ("🔍", "Je recherche : {ctx}"),
    "web_extract": ("📄", "Je lis {ctx}"),
    "x_search": ("🐦", "Je cherche sur X (Twitter)"),
    # Navigateur automatisé
    "browser_navigate": ("🌐", "Je consulte {ctx}"),
    "browser_snapshot": ("📸", "J'analyse la page"),
    "browser_vision": ("👁️", "J'observe la page"),
    "browser_get_images": ("🖼️", "Je regarde les images de la page"),
    "browser_click": ("👆", "Je clique sur la page"),
    "browser_type": ("⌨️", "Je saisis du texte"),
    "browser_scroll": ("📜", "Je fais défiler la page"),
    "browser_back": ("◀️", "Je reviens à la page précédente"),
    "browser_press": ("⌨️", "J'utilise le clavier"),
    "browser_console": ("🖥️", "J'inspecte la page"),
    "browser_dialog": ("💬", "Je gère une fenêtre de la page"),
    # Fichiers & code (phrases neutres : on n'expose pas les chemins/commandes techniques)
    "read_file": ("📖", "Je lis un document"),
    "write_file": ("✍️", "Je rédige un document"),
    "patch": ("🔧", "Je mets à jour un document"),
    "search_files": ("🔎", "Je cherche dans les documents"),
    "terminal": ("💻", "J'exécute une opération technique"),
    "read_terminal": ("🖥️", "Je consulte le résultat"),
    "process": ("⚙️", "Je lance une tâche de fond"),
    "execute_code": ("🐍", "J'exécute un calcul"),
    # Mémoire & organisation
    "memory": ("🧠", "Je consulte ma mémoire"),
    "session_search": ("🔍", "Je me remémore nos échanges"),
    "todo": ("📋", "J'organise mes tâches"),
    "clarify": ("❓", "Je réfléchis à ta demande"),
    "delegate_task": ("🔀", "Je délègue à un agent spécialisé"),
    "lunaria_long_mission": ("⏳", "Mission approfondie en cours {ctx}"),
    "mixture_of_agents": ("🧠", "Je fais réfléchir plusieurs modèles"),
    "cronjob": ("⏰", "Je programme une automatisation"),
    # Compétences
    "skills_list": ("📚", "Je consulte mes compétences"),
    "skill_view": ("📚", "Je consulte une compétence"),
    "skill_manage": ("📝", "Je mets à jour une compétence"),
    # Génération de médias
    "image_generate": ("🎨", "Je génère une image"),
    "video_generate": ("🎬", "Je génère une vidéo"),
    "text_to_speech": ("🔊", "Je génère l'audio"),
    "vision_analyze": ("👁️", "J'analyse l'image"),
    "video_analyze": ("🎬", "J'analyse la vidéo"),
}

# Repli par FAMILLE (préfixe du nom d'outil) : phrase complète, sans contexte technique.
_FAMILY_TEMPLATES: tuple[tuple[str, tuple[str, str]], ...] = (
    ("browser_", ("🌐", "Je navigue sur le web")),
    ("web_", ("🔍", "Je cherche des informations")),
    ("kanban_", ("📋", "Je mets à jour le tableau des tâches")),
    ("skill", ("📚", "Je consulte mes compétences")),
    ("ha_", ("🏠", "Je pilote la domotique")),
    ("memory", ("🧠", "Je consulte ma mémoire")),
    ("read_", ("📖", "Je consulte un document")),
    ("write_", ("✍️", "Je rédige un document")),
    ("file", ("📁", "Je travaille sur des documents")),
    ("image", ("🎨", "Je travaille sur une image")),
    ("video", ("🎬", "Je travaille sur une vidéo")),
)

_GENERIC = ("⚙️", "Je travaille sur ta demande")

_MAX_CTX = 60


def _clean_context(label: str) -> str:
    """Nettoie le label pour l'affichage : URL → domaine (sans www), sinon texte tronqué."""
    label = (label or "").strip()
    if not label:
        return ""
    if label.startswith(("http://", "https://")):
        try:
            host = urlparse(label).netloc
        except ValueError:
            return ""
        return host[4:] if host.startswith("www.") else host
    label = " ".join(label.split())  # une seule ligne
    return (label[: _MAX_CTX - 1] + "…") if len(label) > _MAX_CTX else label


def _family_for(tool: str) -> tuple[str, str] | None:
    for prefix, tmpl in _FAMILY_TEMPLATES:
        if tool.startswith(prefix):
            return tmpl
    return None


def humanize_tool_progress(tool: str, label: str = "") -> str:
    """Phrase FR lisible pour une étape de travail de l'agent.

    Ex. humanize_tool_progress("browser_navigate", "https://www.techcrunch.com/x")
        → « 🌐 Je consulte techcrunch.com »
        humanize_tool_progress("web_search", "meilleurs CRM 2026")
        → « 🔍 Je recherche : meilleurs CRM 2026 »
        humanize_tool_progress("un_outil_inconnu") → « ⚙️ Je travaille sur ta demande »
    """
    tool = (tool or "").strip()
    ctx = _clean_context(label)
    entry = _TOOL_TEMPLATES.get(tool)
    if entry:
        emoji, template = entry
        if "{ctx}" in template:
            if ctx:
                return f"{emoji} {template.format(ctx=ctx)}".strip()
            # Label attendu mais vide/illisible → on retombe sur le repli de famille.
        else:
            return f"{emoji} {template}".strip()
    emoji, phrase = _family_for(tool) or _GENERIC
    return f"{emoji} {phrase}".strip()
