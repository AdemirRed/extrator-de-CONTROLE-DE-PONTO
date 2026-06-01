"""
Exportação no FORMATO ANTIGO (CARTÃO PONTO.html / V3).

Converte o formato novo (funcionarios + registros + feriados + config)
para o formato antigo, compatível com o "Importar JSON":
  - registros["YYYY-MM-DD"] → funcionario.meses["ano-M"][dia-1]  (M = mês 0-indexado)
  - inicio_intervalo/fim_intervalo → inicioInt/fimInt
  - feriados "YYYY-MM-DD" → "ano-M-D"
  - config.schedule → schedule (já em chave JS getDay)
"""

import calendar
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.storage import load

router = APIRouter(prefix="/api", tags=["exportar"])


def _empty_rows(ano: int, mes_real: int) -> list[dict]:
    n = calendar.monthrange(ano, mes_real)[1]
    return [{"dia": d, "entrada": "", "inicioInt": "", "fimInt": "", "saida": ""}
            for d in range(1, n + 1)]


@router.get("/exportar-json")
def exportar_json():
    data = load()
    cfg  = data.get("config", {})

    # ── Funcionários + meses ──
    funcionarios_out = []
    anos_vistos = set()

    for func in data.get("funcionarios", []):
        if not func.get("ativo", True):
            continue
        fid = str(func["id"])
        regs = data.get("registros", {}).get(fid, {})

        meses: dict[str, list] = {}
        for data_str, r in regs.items():
            try:
                ano, mes_real, dia = map(int, data_str.split("-"))
            except ValueError:
                continue
            anos_vistos.add(ano)
            mes0 = mes_real - 1                     # real → 0-indexado (formato antigo)
            key  = f"{ano}-{mes0}"
            if key not in meses:
                meses[key] = _empty_rows(ano, mes_real)
            if 1 <= dia <= len(meses[key]):
                meses[key][dia - 1] = {
                    "dia":       dia,
                    "entrada":   r.get("entrada") or "",
                    "inicioInt": r.get("inicio_intervalo") or "",
                    "fimInt":    r.get("fim_intervalo") or "",
                    "saida":     r.get("saida") or "",
                }

        funcionarios_out.append({
            "id":     func["id"],
            "nome":   func["nome"],
            "aberto": True,
            "meses":  meses,
        })

    # ── Feriados: "YYYY-MM-DD" → "ano-M-D" (M 0-indexado) ──
    feriados_out = {}
    for ds in data.get("feriados", {}):
        try:
            ano, mes_real, dia = map(int, ds.split("-"))
            feriados_out[f"{ano}-{mes_real-1}-{dia}"] = True
        except ValueError:
            pass

    # ── Schedule (já em chave JS getDay 0..6) ──
    schedule = cfg.get("schedule", {})

    # ── Config no formato antigo ──
    config_out = {
        "noturnoInicio": cfg.get("noturno_inicio", "22:00"),
        "feriadoRate":   int(cfg.get("feriado_rate", 50)),
    }

    ano_atual = max(anos_vistos) if anos_vistos else datetime.now().year

    out = {
        "funcionarios": funcionarios_out,
        "mes":          datetime.now().month - 1,   # 0-indexado
        "ano":          ano_atual,
        "schedule":     schedule,
        "config":       config_out,
        "feriados":     feriados_out,
    }

    return JSONResponse(
        content=out,
        headers={"Content-Disposition": "attachment; filename=cartao_ponto_backup.json"},
    )
