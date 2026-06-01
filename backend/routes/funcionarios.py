"""CRUD de funcionários — armazenamento JSON."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.storage import load, save, next_id

router = APIRouter(prefix="/api/funcionarios", tags=["funcionarios"])


class FuncionarioIn(BaseModel):
    nome: str
    matricula: Optional[str] = None
    cargo: Optional[str] = None
    jornada: Optional[str] = "07:00-17:30"
    int_inicio: Optional[str] = "11:30"
    int_fim: Optional[str] = "13:00"


@router.get("")
def listar():
    data = load()
    return [f for f in data["funcionarios"] if f.get("ativo", True)]


@router.post("", status_code=201)
def criar(f: FuncionarioIn):
    data = load()
    novo = {
        "id":         next_id(data["funcionarios"]),
        "nome":       f.nome,
        "matricula":  f.matricula,
        "cargo":      f.cargo,
        "jornada":    f.jornada or "07:00-17:30",
        "int_inicio": f.int_inicio or "11:30",
        "int_fim":    f.int_fim   or "13:00",
        "ativo":      True,
    }
    data["funcionarios"].append(novo)
    save(data)
    return novo


@router.get("/{fid}")
def obter(fid: int):
    data = load()
    f = next((f for f in data["funcionarios"] if f["id"] == fid), None)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado")
    return f


@router.put("/{fid}")
def atualizar(fid: int, f: FuncionarioIn):
    data = load()
    for i, func in enumerate(data["funcionarios"]):
        if func["id"] == fid:
            data["funcionarios"][i].update({
                "nome":       f.nome,
                "matricula":  f.matricula,
                "cargo":      f.cargo,
                "jornada":    f.jornada,
                "int_inicio": f.int_inicio,
                "int_fim":    f.int_fim,
            })
            save(data)
            return data["funcionarios"][i]
    raise HTTPException(404, "Funcionário não encontrado")


@router.delete("/{fid}")
def remover(fid: int):
    data = load()
    for func in data["funcionarios"]:
        if func["id"] == fid:
            func["ativo"] = False
            save(data)
            return {"ok": True}
    raise HTTPException(404, "Funcionário não encontrado")
