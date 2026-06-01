"""
Armazenamento em arquivo JSON local.
Tudo salvo em database/ponto.json — sem banco de dados.
"""

import json
import threading
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "database" / "ponto.json"
_lock = threading.Lock()

DEFAULT = {
    "funcionarios": [],   # [{id, nome, jornada, int_inicio, int_fim, cargo, matricula}]
    "registros": {},      # {"func_id": {"YYYY-MM-DD": {campos...}}}
    "feriados": {},       # {"YYYY-MM-DD": "Nome do feriado"}
    "config": {
        "noturno_inicio": "22:00",
        "noturno_fim":    "05:00",
        "he_50_pct":      "50",
        "he_100_pct":     "100",
        "conf_minima":    "0.65",
        "feriado_rate":   "50",
        # Escala por dia-da-semana (chave = JS getDay: 0=Dom .. 6=Sáb)
        "schedule": {
            "0": {"ativo": False, "entrada": "07:00", "intInicio": "11:30", "intFim": "13:00", "saida": "12:00"},
            "1": {"ativo": True,  "entrada": "07:00", "intInicio": "11:30", "intFim": "13:00", "saida": "17:30"},
            "2": {"ativo": True,  "entrada": "07:00", "intInicio": "11:30", "intFim": "13:00", "saida": "17:30"},
            "3": {"ativo": True,  "entrada": "07:00", "intInicio": "11:30", "intFim": "13:00", "saida": "17:30"},
            "4": {"ativo": True,  "entrada": "07:00", "intInicio": "11:30", "intFim": "13:00", "saida": "17:30"},
            "5": {"ativo": True,  "entrada": "07:00", "intInicio": "11:30", "intFim": "13:00", "saida": "16:30"},
            "6": {"ativo": False, "entrada": "07:00", "intInicio": "11:30", "intFim": "13:00", "saida": "12:00"},
        },
    },
}


def load() -> dict:
    DATA_FILE.parent.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        return _deep_copy(DEFAULT)
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        # Garante que as chaves obrigatórias existem
        for k, v in DEFAULT.items():
            if k not in data:
                data[k] = _deep_copy(v)
        # Garante sub-chaves do config (ex.: schedule) em bancos antigos
        for ck, cv in DEFAULT["config"].items():
            if ck not in data.get("config", {}):
                data.setdefault("config", {})[ck] = _deep_copy(cv)
        return data
    except Exception:
        return _deep_copy(DEFAULT)


def save(data: dict):
    with _lock:
        DATA_FILE.parent.mkdir(exist_ok=True)
        DATA_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


def _deep_copy(obj):
    return json.loads(json.dumps(obj))


def next_id(items: list) -> int:
    if not items:
        return 1
    return max(i.get("id", 0) for i in items) + 1
