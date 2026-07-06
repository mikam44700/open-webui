from __future__ import annotations

import logging

import black
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from open_webui.config import DATA_DIR, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.models.chats import ChatTitleMessagesForm
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.code_interpreter import execute_code_jupyter
from open_webui.utils.misc import get_gravatar_url
from open_webui.utils.pdf_generator import PDFGenerator
from pydantic import BaseModel
from starlette.responses import FileResponse

log = logging.getLogger(__name__)

router = APIRouter()


@router.get('/gravatar')
async def get_gravatar(email: str, user=Depends(get_verified_user)):
    return get_gravatar_url(email)


class CodeForm(BaseModel):
    code: str


@router.post('/code/format')
async def format_code(form_data: CodeForm, user=Depends(get_admin_user)):
    try:
        formatted_code = black.format_str(form_data.code, mode=black.Mode())
        return {'code': formatted_code}
    except black.NothingChanged:
        return {'code': form_data.code}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/code/execute')
async def execute_code(request: Request, form_data: CodeForm, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_CODE_EXECUTION:
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.FEATURE_DISABLED('Code execution'),
        )

    if request.app.state.config.CODE_EXECUTION_ENGINE == 'jupyter':
        output = await execute_code_jupyter(
            request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
            form_data.code,
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == 'token'
                else None
            ),
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == 'password'
                else None
            ),
            request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        )

        return output
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.DEFAULT('Code execution engine not supported'),
        )


class ChatForm(BaseModel):
    title: str
    messages: list[dict]


@router.post('/pdf')
async def download_chat_as_pdf(form_data: ChatTitleMessagesForm, user=Depends(get_verified_user)):
    try:
        pdf_bytes = PDFGenerator(form_data).generate_chat_pdf()

        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': 'attachment;filename=chat.pdf'},
        )
    except Exception as e:
        log.exception(f'Error generating PDF: {e}')
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/media/download')
async def download_media(url: str, user=Depends(get_verified_user)):
    """Proxy de téléchargement pour les médias générés (images/vidéos).

    Les CDN des fournisseurs (ex. files-cdn.x.ai) bloquent le téléchargement direct
    depuis le navigateur (CORS) → le bouton « télécharger » ouvrait juste un onglet.
    On récupère le média côté serveur (même origine pour le front) et on le renvoie
    avec ``Content-Disposition: attachment`` pour forcer un vrai téléchargement.

    Garde-fous anti-SSRF : HTTPS uniquement, hôtes internes bloqués, et on ne renvoie
    QUE des contenus image/* ou video/* (taille plafonnée)."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    import httpx

    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='URL invalide')
    # Bloque localhost / IP privées (SSRF).
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Hôte non autorisé')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Hôte injoignable')

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail='Téléchargement impossible')

    ctype = resp.headers.get('content-type', 'application/octet-stream').split(';')[0].strip()
    if not (ctype.startswith('image/') or ctype.startswith('video/')):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Type de média non autorisé')
    if len(resp.content) > 200 * 1024 * 1024:  # 200 Mo de garde-fou
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Média trop volumineux')

    filename = (parsed.path.rsplit('/', 1)[-1] or 'media').split('?')[0] or 'media'
    return Response(
        content=resp.content,
        media_type=ctype,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/db/download')
async def download_db(user=Depends(get_admin_user)):
    """Download the raw SQLite database file (admin-only, SQLite deployments only)."""
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    # Lazy import avoids circular dependency at module load time
    from open_webui.internal.db import engine

    if engine.name != 'sqlite':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DB_NOT_SQLITE)

    return FileResponse(
        str(engine.url.database),
        media_type='application/octet-stream',
        filename='webui.db',
    )
