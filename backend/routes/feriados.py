"""Feriados — armazenamento JSON."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.storage import load, save

router = APIRouter(prefix="/api/feriados", tags=["feriados"])


class FeriadoIn(BaseModel):
    data: str
    nome: Optional[str] = None


@router.get("")
def listar(ano: Optional[int] = None):
    data     = load()
    feriados = data.get("feriados", {})
    result   = [{"data": k, "nome": v} for k, v in feriados.items()]
    if ano:
        result = [f for f in result if f["data"].startswith(str(ano))]
    return sorted(result, key=lambda x: x["data"])


@router.post("", status_code=201)
def criar(f: FeriadoIn):
    data = load()
    data.setdefault("feriados", {})[f.data] = f.nome or ""
    save(data)
    return {"ok": True}


@router.delete("/{data_str}")
def remover(data_str: str):
    data = load()
    data.get("feriados", {}).pop(data_str, None)
    save(data)
    return {"ok": True}
