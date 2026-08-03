"""Router Journal — le registre des traitements du moteur.

Le moteur ne sait pas dire ce qu'il a fait : `/v1/runs` est en POST seul, sans
route de liste. Un traitement declenche depuis Telegram ou par une tache
planifiee ne laisse donc aucune trace consultable. Ce journal est cette trace,
ecrite cote Open WebUI par le proxy — le seul point par lequel tout passe deja.

Trois regles tenues ici :

  1. **Ecrire ne doit jamais casser ce qu'on enregistre.** Une panne du journal
     ne fait pas echouer le traitement : `HermesActivities.insert` avale ses
     erreurs et rend `None`.

  2. **Quatre etats, pas deux.** `unknown` (moteur injoignable, statut absent)
     n'est pas une panne du traitement et ne doit jamais etre affiche comme
     telle. Seul `error` est un echec reel. `pending` porte le produit : le
     moteur a prepare, un humain doit signer.

  3. **Le journal se lit par tout utilisateur verifie, pas seulement par
     l'administrateur.** C'est deliberé : la personne qui fait le travail doit
     voir son travail. Une instance sert une seule entreprise, le flux traite
     est celui de l'entreprise, pas celui d'un individu.

Sur l'ecriture, une limite qu'il faut connaitre : **Open WebUI ne peut pas
observer ce qui se passe sur Telegram.** Ces traitements partent du moteur sans
jamais traverser ce serveur. Le journal ne les espionne donc pas — c'est le
moteur qui les **declare**, par `POST /`. Cette route est le point d'entree
prevu pour la cle d'API du moteur, a restreindre par `API_KEYS_ALLOWED_ENDPOINTS`
pour qu'elle ne puisse rien faire d'autre.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from open_webui.models.hermes_activity import (
    SOURCES,
    STATUSES,
    HermesActivities,
    HermesActivityCounts,
    HermesActivityForm,
    HermesActivityModel,
)
from open_webui.utils.auth import get_verified_user
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

# Fenetres proposees par l'ecran d'accueil. Bornees pour qu'une URL fabriquee a
# la main ne puisse pas demander un balayage complet de la table.
FENETRES = {
    'jour': 24 * 60 * 60,
    'semaine': 7 * 24 * 60 * 60,
    'mois': 30 * 24 * 60 * 60,
}

LIMITE_MAX = 200


def _borne_inferieure(fenetre: Optional[str]) -> Optional[int]:
    if fenetre is None or fenetre == 'tout':
        return None
    duree = FENETRES.get(fenetre)
    if duree is None:
        raise HTTPException(
            status_code=400,
            detail=f"Fenetre inconnue. Valeurs acceptees : {', '.join(FENETRES)}, tout.",
        )
    return int(time.time()) - duree


class SyntheseJournal(BaseModel):
    """Ce que l'ecran d'accueil affiche, deja compte cote serveur."""

    fenetre: str
    compteurs: HermesActivityCounts
    dernieres: list[HermesActivityModel]


@router.get('/', response_model=list[HermesActivityModel])
async def lister(
    limit: int = Query(50, ge=1, le=LIMITE_MAX),
    skip: int = Query(0, ge=0),
    statut: Optional[str] = None,
    source: Optional[str] = None,
    fenetre: Optional[str] = None,
    user=Depends(get_verified_user),
):
    if statut is not None and statut not in STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Statut inconnu. Valeurs acceptees : {', '.join(STATUSES)}.",
        )
    if source is not None and source not in SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Source inconnue. Valeurs acceptees : {', '.join(SOURCES)}.",
        )

    return await HermesActivities.list(
        limit=limit,
        skip=skip,
        status=statut,
        source=source,
        since=_borne_inferieure(fenetre),
    )


@router.get('/synthese', response_model=SyntheseJournal)
async def synthese(
    fenetre: str = Query('jour'),
    apercu: int = Query(10, ge=0, le=50),
    user=Depends(get_verified_user),
):
    """Compteurs et dernieres lignes, en une seule requete.

    L'ecran d'accueil a besoin des deux ensemble : deux allers-retours
    afficheraient un total et une liste pris a deux instants differents.
    """
    borne = _borne_inferieure(fenetre)

    return SyntheseJournal(
        fenetre=fenetre,
        compteurs=await HermesActivities.counts(since=borne),
        dernieres=await HermesActivities.list(limit=apercu, since=borne) if apercu else [],
    )


@router.post('/', response_model=Optional[HermesActivityModel])
async def enregistrer(form: HermesActivityForm, user=Depends(get_verified_user)):
    """Enregistre un traitement declare par le moteur.

    Rend `null` — et non une erreur — si l'ecriture echoue : le moteur ne doit
    pas reprendre un traitement reussi sous pretexte que le journal a flanche.
    """
    return await HermesActivities.insert(form, user_id=user.id)


@router.get('/{id}', response_model=HermesActivityModel)
async def obtenir(id: str, user=Depends(get_verified_user)):
    entree = await HermesActivities.get_by_id(id)
    if entree is None:
        raise HTTPException(status_code=404, detail='Traitement introuvable.')
    return entree
