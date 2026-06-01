"""
Estado completo — compatível com o CARTÃO PONTO.html.
GET  /api/state      → retorna estado salvo (ou null)
POST /api/state      → salva estado completo
POST /api/state/tema → salva só o tema
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.storage import load, save

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get("")
def get_state():
    data = load()
    return JSONResponse(content=data.get("cartao_ponto_state"))


@router.post("")
async def post_state(request: Request):
    body = await request.json()
    data = load()
    data["cartao_ponto_state"] = body
    save(data)
    return {"ok": True}


@router.post("/tema")
async def post_tema(request: Request):
    body = await request.json()
    # tema salvo dentro do state
    data = load()
    st = data.get("cartao_ponto_state") or {}
    st["_tema"] = body.get("tema", "dark")
    data["cartao_ponto_state"] = st
    save(data)
    return {"ok": True}
