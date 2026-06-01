"""Configurações — armazenamento JSON."""

from fastapi import APIRouter
from backend.storage import load, save

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def obter():
    return load().get("config", {})


@router.post("")
def salvar_config(config: dict):
    data = load()
    cfg = data.setdefault("config", {})
    for k, v in config.items():
        # Preserva objetos aninhados (ex.: schedule) sem convertê-los em string
        cfg[str(k)] = v if isinstance(v, (dict, list)) else str(v)
    save(data)
    return {"ok": True}
