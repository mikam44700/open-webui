import logging
import unicodedata
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import DATA_DIR
from open_webui.internal.db import get_async_session
from open_webui.models.files import FileForm, Files
from open_webui.models.knowledge import KnowledgeForm, Knowledges
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.utils.auth import get_verified_user
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()

VAULT_ROOT = DATA_DIR / 'vault'
MEMOIRE_KB_NAME = "Mémoire d'entreprise"
MAX_FICHE_BYTES = 1024 * 1024

SEED_FOLDERS = ['Clients', 'Prix', 'Procédures', 'Historique']

SEED_FICHES = {
    'Bienvenue.md': (
        '# Bienvenue dans votre Mémoire\n\n'
        "Cette page est le cerveau de votre entreprise : tout ce que vous et vos agents "
        'décidez de retenir vit ici, sous forme de fiches reliées entre elles.\n\n'
        '## Comment ça marche\n\n'
        '- Chaque fiche est un document simple, rangé dans un dossier.\n'
        '- Les fiches se relient entre elles avec des liens : [[Exemple - Ma première fiche]].\n'
        '- Vos dossiers de départ : Clients, Prix, Procédures, Historique. '
        'Créez-en d autres librement.\n\n'
        'Votre assistant s appuie sur ces fiches pour répondre : '
        'plus la mémoire est riche, plus il connaît votre entreprise.\n'
    ),
    'Exemple - Ma première fiche.md': (
        '# Exemple - Ma première fiche\n\n'
        'Une fiche décrit une chose que votre entreprise doit retenir : '
        'un client, un tarif, une procédure, une décision.\n\n'
        'Vous pouvez revenir à la fiche [[Bienvenue]] en cliquant sur le lien.\n'
    ),
}


####################
# Vault filesystem
####################


def get_vault_dir(user_id: str) -> Path:
    vault = (VAULT_ROOT / user_id).resolve()
    if not vault.is_relative_to(VAULT_ROOT.resolve()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())
    if not vault.exists():
        vault.mkdir(parents=True, exist_ok=True)
        for folder in SEED_FOLDERS:
            (vault / folder).mkdir(exist_ok=True)
        for filename, content in SEED_FICHES.items():
            (vault / filename).write_text(content, encoding='utf-8')
    return vault


def resolve_vault_path(user_id: str, rel_path: str, is_fiche: bool = False) -> Path:
    segments = [unicodedata.normalize('NFC', s) for s in rel_path.replace('\\', '/').split('/') if s]
    if not segments:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Chemin vide')
    for segment in segments:
        if segment in ('.', '..') or '\x00' in segment or segment.startswith('~') or len(segment) > 120:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Chemin invalide')
    if is_fiche and not segments[-1].endswith('.md'):
        segments[-1] = f'{segments[-1]}.md'

    vault = get_vault_dir(user_id)
    target = (vault / Path(*segments)).resolve()
    if not target.is_relative_to(vault):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Chemin invalide')
    return target


def build_tree(directory: Path, vault: Path) -> list[dict]:
    entries = []
    folders = sorted([p for p in directory.iterdir() if p.is_dir() and not p.name.startswith('.')])
    fiches = sorted([p for p in directory.iterdir() if p.is_file() and p.suffix == '.md'])
    for folder in folders:
        entries.append(
            {
                'name': folder.name,
                'path': str(folder.relative_to(vault)),
                'type': 'dossier',
                'children': build_tree(folder, vault),
            }
        )
    for fiche in fiches:
        entries.append(
            {
                'name': fiche.stem,
                'path': str(fiche.relative_to(vault)),
                'type': 'fiche',
            }
        )
    return entries


####################
# Indexation (Connaissances / RAG)
####################


async def get_or_create_memoire_kb(user, db: AsyncSession):
    # The KB id is pinned in the vault: renaming the KB in the Connaissances
    # screen must not silently detach the Mémoire from its index.
    kb_id_file = get_vault_dir(user.id) / '.memoire_kb'
    if kb_id_file.is_file():
        kb = await Knowledges.get_knowledge_by_id(kb_id_file.read_text(encoding='utf-8').strip(), db=db)
        if kb and kb.user_id == user.id:
            return kb

    knowledge_bases = await Knowledges.get_knowledge_bases_by_user_id(user.id, 'write', db=db)
    kb = next(
        (k for k in knowledge_bases if k.user_id == user.id and k.name == MEMOIRE_KB_NAME),
        None,
    )
    if kb is None:
        kb = await Knowledges.insert_new_knowledge(
            user.id,
            KnowledgeForm(
                name=MEMOIRE_KB_NAME,
                description='Les fiches de votre page Mémoire, consultables par votre assistant.',
            ),
            db=db,
        )
    if kb:
        kb_id_file.write_text(kb.id, encoding='utf-8')
    return kb


async def index_fiche(request: Request, user, rel_path: str, content: str, db: AsyncSession) -> None:
    kb = await get_or_create_memoire_kb(user, db=db)
    if not kb:
        raise RuntimeError('Base de connaissances Mémoire introuvable')

    existing = None
    for file in await Knowledges.get_files_by_id(kb.id, db=db):
        if (file.meta or {}).get('vault_path') == rel_path:
            existing = file
            break

    if existing:
        file_id = existing.id
        await Files.update_file_data_by_id(file_id, {'content': content}, db=db)
    else:
        file_id = str(uuid.uuid4())
        filename = Path(rel_path).name
        await Files.insert_new_file(
            user.id,
            FileForm(
                id=file_id,
                filename=filename,
                path=str(resolve_vault_path(user.id, rel_path, is_fiche=True)),
                data={'content': content},
                meta={'name': filename, 'content_type': 'text/markdown', 'vault_path': rel_path},
            ),
            db=db,
        )
    await process_file(
        request,
        ProcessFileForm(file_id=file_id, content=content, collection_name=kb.id),
        user=user,
        db=db,
    )

    if not existing:
        await Knowledges.add_file_to_knowledge_by_id(kb.id, file_id, user.id, db=db)


####################
# Routes
####################


class FicheForm(BaseModel):
    path: str
    content: str


class DossierForm(BaseModel):
    path: str


@router.get('/tree')
async def get_tree(user=Depends(get_verified_user)):
    vault = get_vault_dir(user.id)
    return {'tree': build_tree(vault, vault)}


@router.get('/fiche')
async def get_fiche(path: str, user=Depends(get_verified_user)):
    target = resolve_vault_path(user.id, path, is_fiche=True)
    if not target.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return {'path': path, 'content': target.read_text(encoding='utf-8')}


@router.post('/fiche')
async def save_fiche(
    request: Request,
    form_data: FicheForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if len(form_data.content.encode('utf-8')) > MAX_FICHE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Fiche trop volumineuse')

    target = resolve_vault_path(user.id, form_data.path, is_fiche=True)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(form_data.content, encoding='utf-8')
    except OSError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail='Chemin invalide : une fiche porte déjà ce nom à cet emplacement',
        )

    vault = get_vault_dir(user.id)
    rel_path = str(target.relative_to(vault))

    indexed = True
    try:
        await index_fiche(request, user, rel_path, form_data.content, db=db)
    except Exception as e:
        # The fiche on disk is the source of truth; indexing is retried on next save.
        indexed = False
        log.exception(f'Indexation Mémoire échouée pour {rel_path}: {e}')

    return {'path': rel_path, 'indexed': indexed}


@router.post('/dossier')
async def create_dossier(form_data: DossierForm, user=Depends(get_verified_user)):
    target = resolve_vault_path(user.id, form_data.path)
    if target.suffix == '.md':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Chemin invalide')
    target.mkdir(parents=True, exist_ok=True)
    vault = get_vault_dir(user.id)
    return {'path': str(target.relative_to(vault))}
