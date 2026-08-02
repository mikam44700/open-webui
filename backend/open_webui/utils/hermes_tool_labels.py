"""Translate Hermes tool lifecycle events into client-safe French sentences."""

from __future__ import annotations

from urllib.parse import urlparse


_TOOL_TEMPLATES: dict[str, tuple[str, str]] = {
    'web_search': ('Recherche en cours', 'Je recherche : {context}'),
    'web_extract': ('Lecture en cours', 'Je consulte {context}'),
    'browser_navigate': ('Navigation en cours', 'Je consulte {context}'),
    'browser_snapshot': ('Analyse en cours', "J'analyse la page"),
    'browser_vision': ('Analyse en cours', "J'observe la page"),
    'browser_get_images': ('Analyse en cours', "J'examine les images"),
    'browser_click': ('Action en cours', "J'interagis avec la page"),
    'browser_type': ('Saisie en cours', 'Je renseigne les informations'),
    'browser_scroll': ('Lecture en cours', 'Je poursuis la lecture'),
    'read_file': ('Lecture en cours', 'Je lis un document'),
    'write_file': ('Rédaction en cours', 'Je rédige un document'),
    'patch': ('Mise à jour en cours', 'Je mets à jour un document'),
    'search_files': ('Recherche en cours', 'Je cherche dans les documents'),
    'terminal': ('Opération en cours', "J'exécute une opération technique"),
    'read_terminal': ('Vérification en cours', 'Je vérifie le résultat'),
    'process': ('Traitement en cours', 'Je lance une tâche de fond'),
    'execute_code': ('Calcul en cours', "J'effectue le calcul"),
    'memory': ('Mémoire en cours', 'Je consulte ma mémoire'),
    'session_search': ('Mémoire en cours', 'Je retrouve nos échanges'),
    'todo': ('Organisation en cours', "J'organise les tâches"),
    'clarify': ('Analyse en cours', "J'analyse la demande"),
    'delegate_task': ('Délégation en cours', 'Je sollicite un spécialiste'),
    'cronjob': ('Planification en cours', 'Je prépare une automatisation'),
    'skills_list': ('Préparation en cours', 'Je consulte mes compétences'),
    'skill_view': ('Préparation en cours', 'Je consulte une compétence'),
    'skill_manage': ('Mise à jour en cours', 'Je mets à jour une compétence'),
    'image_generate': ('Création en cours', 'Je génère une image'),
    'video_generate': ('Création en cours', 'Je génère une vidéo'),
    'text_to_speech': ('Création en cours', "Je génère l'audio"),
    'vision_analyze': ('Analyse en cours', "J'analyse l'image"),
    'video_analyze': ('Analyse en cours', "J'analyse la vidéo"),
}

_FAMILY_TEMPLATES: tuple[tuple[str, tuple[str, str]], ...] = (
    ('browser_', ('Navigation en cours', 'Je navigue sur le web')),
    ('web_', ('Recherche en cours', 'Je cherche les informations')),
    ('kanban_', ('Organisation en cours', 'Je mets à jour les tâches')),
    ('skill', ('Préparation en cours', 'Je consulte mes compétences')),
    ('memory', ('Mémoire en cours', 'Je consulte ma mémoire')),
    ('read_', ('Lecture en cours', 'Je consulte un document')),
    ('write_', ('Rédaction en cours', 'Je rédige un document')),
    ('file', ('Document en cours', 'Je travaille sur les documents')),
    ('image', ('Création en cours', "Je travaille sur l'image")),
    ('video', ('Création en cours', 'Je travaille sur la vidéo')),
)

_GENERIC = ('Travail en cours', 'Je travaille sur votre demande')
_MAX_CONTEXT = 60


def _clean_context(label: str) -> str:
    value = (label or '').strip()
    if not value:
        return ''
    if value.startswith(('http://', 'https://')):
        try:
            host = urlparse(value).netloc
        except ValueError:
            return ''
        return host[4:] if host.startswith('www.') else host
    value = ' '.join(value.split())
    return f'{value[: _MAX_CONTEXT - 1]}…' if len(value) > _MAX_CONTEXT else value


def humanize_tool_progress(tool: str, label: str = '') -> tuple[str, str]:
    """Return a short title and a safe description for a Hermes tool."""
    tool_name = (tool or '').strip()
    context = _clean_context(label)
    entry = _TOOL_TEMPLATES.get(tool_name)

    if entry:
        title, template = entry
        if '{context}' not in template:
            return title, template
        if context:
            return title, template.format(context=context)

    for prefix, fallback in _FAMILY_TEMPLATES:
        if tool_name.startswith(prefix):
            return fallback
    return _GENERIC

