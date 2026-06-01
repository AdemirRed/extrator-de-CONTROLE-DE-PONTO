"""
Backup do banco de dados completo (funcionarios + registros + feriados + config).
GET  /api/backup  → baixa o JSON completo
POST /api/backup  → substitui todo o banco pelo JSON enviado
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from backend.storage import load, save

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("")
def exportar():
    data = load()
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=banco_cartao_ponto.json"},
    )


@router.post("")
async def importar(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "JSON inválido")

    if not isinstance(body, dict):
        raise HTTPException(400, "Formato inválido")

    # Garante as chaves mínimas
    body.setdefault("funcionarios", [])
    body.setdefault("registros", {})
    body.setdefault("feriados", {})
    body.setdefault("config", {})
    save(body)
    return {"ok": True}
