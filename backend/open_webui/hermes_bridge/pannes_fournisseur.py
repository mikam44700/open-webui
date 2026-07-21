"""Traduction des pannes de fournisseur de modèle en français clair.

Pourquoi ce module (leçon du 2026-07-21) : quand le compte xAI de Michael a atteint sa
limite, le chat a affiché ceci DANS LA BULLE DE L'AGENT, comme si le collègue parlait :

    HTTP 403: {"code":"permission-denied","error":"Your team eae9ddd5-3390-42a2-9a85-...
    has either used all available credits or reached its monthly spending limit..."}

Quatre défauts : c'est l'agent qui semble le dire, c'est en anglais et en jargon, ça
expose l'identifiant d'équipe du fournisseur, et personne ne dit quoi faire. Pour un
produit vendu 200-450 EUR/mois à des dirigeants non techniques, c'est inacceptable — et
ces pannes-là ARRIVERONT chez les clients (clé expirée, quota de fin de mois, incident).

Le module reconnaît les pannes par leur signature textuelle plutôt que par le code HTTP :
les fournisseurs ne s'accordent ni sur les codes ni sur les formats, mais leurs messages
contiennent des expressions stables. Une panne non reconnue est rendue générique — jamais
le texte brut, qui peut contenir des identifiants internes.
"""

from __future__ import annotations

import re

# Marqueur en tête d'un contenu d'agent : le moteur Hermes renvoie parfois HTTP 200 avec
# l'erreur du fournisseur en guise de réponse (finish_reason=error).
_PREFIXE_ERREUR = re.compile(r"^\s*HTTP\s+\d{3}\s*:", re.IGNORECASE)

# Toutes les pannes ne portent pas ce préfixe : celles du MOTEUR lui-même arrivent en
# texte nu (« No LLM provider configured. Run `hermes model`… » — passé au travers du
# filtre le 2026-07-21). Signatures reconnaissables sans ambiguïté : jamais un agent ne
# répond ça à un dirigeant.
_SIGNATURES_NUES = (
    "no llm provider configured",
    "no inference provider configured",
    "run `hermes ",
    "run 'hermes ",
    "traceback (most recent call last)",
    "connection refused",
    "econnrefused",
)

# (signatures à chercher en minuscules, message français). Ordre = priorité : la première
# règle qui correspond gagne, donc les cas précis avant les cas génériques.
_REGLES: list[tuple[tuple[str, ...], str]] = [
    (
        ("used all available credits", "spending limit", "insufficient_quota", "insufficient credits", "billing_hard_limit"),
        "Le compte du fournisseur de modèle IA a atteint sa limite : il n’y a plus de "
        "crédit disponible pour ce mois. Rendez-vous dans **Capacités → Modèles IA** pour "
        "recharger le compte ou relever la limite de dépense, puis relancez la conversation.",
    ),
    (
        ("no inference provider configured", "no llm provider configured", "run `hermes model", "hermes setup"),
        "Votre équipe est prête, mais aucun modèle IA n’est sélectionné. Rendez-vous dans "
        "**Capacités → Modèles IA** : connectez un compte dans l’onglet « Comptes », puis "
        "choisissez-le comme moteur dans l’onglet « Moteur ».",
    ),
    (
        ("invalid api key", "incorrect api key", "invalid_api_key", "authentication_error", "unauthorized"),
        "La clé du fournisseur de modèle IA n’est pas acceptée : elle est invalide, "
        "expirée ou révoquée. Rendez-vous dans **Capacités → Modèles IA** pour la "
        "remplacer, puis relancez la conversation.",
    ),
    (
        ("rate limit", "rate_limit", "too many requests", "429"),
        "Le fournisseur de modèle IA reçoit trop de demandes à la fois. Patientez une "
        "minute puis relancez la conversation — rien n’est perdu.",
    ),
    (
        ("model not found", "model_not_found", "does not exist", "unknown model"),
        "Le modèle configuré n’existe plus chez le fournisseur. Rendez-vous dans "
        "**Capacités → Modèles IA** pour en choisir un autre, puis relancez la conversation.",
    ),
    (
        ("overloaded", "service unavailable", "503", "502", "bad gateway", "temporarily unavailable"),
        "Le fournisseur de modèle IA est momentanément indisponible — c’est une panne de "
        "son côté, pas de la vôtre. Réessayez dans quelques minutes.",
    ),
    (
        ("timeout", "timed out", "connection error", "connection refused"),
        "Le fournisseur de modèle IA n’a pas répondu à temps. Réessayez dans un instant ; "
        "si cela se répète, vérifiez la connexion internet du serveur.",
    ),
    (
        ("context length", "context_length_exceeded", "too long", "maximum context"),
        "La conversation est devenue trop longue pour le modèle. Démarrez une nouvelle "
        "conversation — vos documents et vos données sont conservés.",
    ),
]

_GENERIQUE = (
    "Le fournisseur de modèle IA a refusé la demande. Rendez-vous dans "
    "**Capacités → Modèles IA** pour vérifier la configuration, puis relancez la "
    "conversation. Si le problème persiste, contactez le support LunarIA."
)

_ENTETE = "**Je ne peux pas répondre pour le moment.**\n\n"


def message_panne(texte_brut: str | None) -> str:
    """Rend le message français correspondant à la panne décrite dans `texte_brut`.

    Une panne non reconnue rend le message générique : on ne recopie JAMAIS le texte du
    fournisseur, qui peut contenir un identifiant de compte ou d'équipe.
    """
    minuscules = (texte_brut or "").lower()
    for signatures, message in _REGLES:
        if any(signature in minuscules for signature in signatures):
            return _ENTETE + message
    return _ENTETE + _GENERIQUE


def ressemble_a_une_panne(contenu: str | None) -> bool:
    """Vrai si ce contenu d'agent est en réalité une erreur technique déguisée.

    Le moteur peut renvoyer HTTP 200 avec l'erreur du fournisseur en guise de réponse :
    dans ce cas le texte commence par « HTTP <code>: » suivi de la charge du fournisseur.
    """
    if not contenu:
        return False
    if _PREFIXE_ERREUR.match(contenu):
        return True
    debut = contenu[:400].lower()
    return any(signature in debut for signature in _SIGNATURES_NUES)
