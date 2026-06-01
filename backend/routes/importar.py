"""
Importação do JSON exportado pelo sistema antigo (CARTÃO PONTO.html / V3).

Converte o formato antigo para o formato da interface NOVA:
  - meses["ano-M"]  (M = mês 0-indexado!) → registros por data "YYYY-MM-DD"
  - campos inicioInt/fimInt → inicio_intervalo/fim_intervalo
  - calcula total/previsto/saldo/noturno usando a escala por dia-da-semana
  - feriados "ano-M-D" → "YYYY-MM-DD"
  - schedule → jornada do funcionário
"""

import json
import calendar
from datetime import date
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.storage import load, save, next_id
from backend.utils.calculations import calc_dia

router = APIRouter(prefix="/api", tags=["importar"])


def _py_to_js_weekday(d: date) -> int:
    """Python weekday() 0=Seg..6=Dom → JS getDay() 0=Dom..6=Sáb."""
    return (d.weekday() + 1) % 7


def _sched_for(schedule: dict, js_weekday: int) -> dict | None:
    """Retorna a escala do dia-da-semana (chave string '0'..'6') se ativa."""
    s = schedule.get(str(js_weekday))
    if s and s.get("ativo"):
        return s
    return None


@router.post("/importar-json")
async def importar_json(file: UploadFile = File(...)):
    content = await file.read()
    try:
        source = json.loads(content)
    except Exception:
        raise HTTPException(400, "Arquivo JSON inválido")

    if "funcionarios" not in source or not isinstance(source["funcionarios"], list):
        raise HTTPException(400, "JSON inválido: campo 'funcionarios' ausente")

    schedule     = source.get("schedule", {})
    feriados_src = source.get("feriados", {})
    config_src   = source.get("config", {})
    noturno_ini  = config_src.get("noturnoInicio", "22:00")

    # Jornada padrão a partir da escala de segunda-feira (js weekday 1)
    seg = schedule.get("1", {})
    jornada    = f"{seg.get('entrada','07:00')}-{seg.get('saida','17:30')}"
    int_inicio = seg.get("intInicio", "11:30")
    int_fim    = seg.get("intFim", "13:00")

    data = load()
    data.setdefault("funcionarios", [])
    data.setdefault("registros", {})
    data.setdefault("feriados", {})
    data.setdefault("config", {})

    # ── Feriados: "ano-M-D" (M 0-indexado) → "YYYY-MM-DD" ──
    feriados_norm = {}   # set de datas normalizadas para uso no cálculo
    for chave in feriados_src:
        parts = chave.split("-")
        if len(parts) == 3:
            try:
                ano, mes0, dia = int(parts[0]), int(parts[1]), int(parts[2])
                ds = f"{ano}-{mes0+1:02d}-{dia:02d}"  # +1: mês 0-indexado → real
                data["feriados"][ds] = ""
                feriados_norm[ds] = True
            except ValueError:
                pass

    # ── Config (inclui a escala por dia-da-semana do sistema antigo) ──
    data["config"]["noturno_inicio"] = noturno_ini
    if config_src.get("feriadoRate") is not None:
        data["config"]["feriado_rate"] = str(config_src.get("feriadoRate"))
    if schedule:
        # schedule antigo já usa chave JS getDay (0=Dom..6=Sáb) — armazena direto
        data["config"]["schedule"] = schedule

    total_funcs = 0
    total_regs  = 0

    for func_src in source["funcionarios"]:
        nome = (func_src.get("nome") or "").strip()
        if not nome:
            continue

        # Busca funcionário existente por nome
        existing = next((f for f in data["funcionarios"]
                         if f.get("nome","").upper() == nome.upper() and f.get("ativo", True)), None)
        if existing:
            func_id = existing["id"]
            existing["jornada"]    = jornada
            existing["int_inicio"] = int_inicio
            existing["int_fim"]    = int_fim
        else:
            func_id = func_src.get("id") if isinstance(func_src.get("id"), int) else next_id(data["funcionarios"])
            # Garante id único
            if any(f["id"] == func_id for f in data["funcionarios"]):
                func_id = next_id(data["funcionarios"])
            data["funcionarios"].append({
                "id":         func_id,
                "nome":       nome,
                "matricula":  func_src.get("matricula"),
                "cargo":      func_src.get("cargo"),
                "jornada":    jornada,
                "int_inicio": int_inicio,
                "int_fim":    int_fim,
                "ativo":      True,
            })
            total_funcs += 1

        fid = str(func_id)
        data["registros"].setdefault(fid, {})

        # ── Converte meses ──
        meses = func_src.get("meses", {})
        for mes_key, dias in meses.items():
            parts = mes_key.split("-")
            if len(parts) != 2:
                continue
            try:
                ano, mes0 = int(parts[0]), int(parts[1])  # mes0 = 0-indexado!
            except ValueError:
                continue
            mes_real = mes0 + 1  # 0-indexado → real (1-12)
            if not (1 <= mes_real <= 12):
                continue

            dias_no_mes = calendar.monthrange(ano, mes_real)[1]

            for reg in dias:
                dia_num = reg.get("dia")
                if not isinstance(dia_num, int) or dia_num < 1 or dia_num > dias_no_mes:
                    continue
                entrada = reg.get("entrada")  or None
                ini_int = reg.get("inicioInt") or None
                fim_int = reg.get("fimInt")    or None
                saida   = reg.get("saida")     or None

                # pula dias completamente vazios
                if not entrada and not saida and not ini_int and not fim_int:
                    continue

                data_str = f"{ano}-{mes_real:02d}-{dia_num:02d}"
                d_obj    = date(ano, mes_real, dia_num)
                js_wd    = _py_to_js_weekday(d_obj)        # 0=Dom..6=Sáb
                py_wd    = d_obj.weekday()                  # 0=Seg..6=Dom
                is_fer   = data_str in feriados_norm
                sched    = _sched_for(schedule, js_wd)
                is_sab   = (js_wd == 6) and (sched is None)  # sábado sem escala

                if sched:
                    s_ent = sched.get("entrada")   or "07:00"
                    s_sai = sched.get("saida")     or "17:30"
                    s_ini = sched.get("intInicio") or "11:30"
                    s_fim = sched.get("intFim")    or "13:00"
                else:
                    s_ent, s_sai, s_ini, s_fim = "07:00", "17:30", "11:30", "13:00"

                calcs = calc_dia(
                    entrada=entrada, inicio_int=ini_int, fim_int=fim_int, saida=saida,
                    sched_inicio=s_ent, sched_fim=s_sai,
                    sched_int_ini=s_ini, sched_int_fim=s_fim,
                    noturno_inicio=noturno_ini,
                    is_feriado=is_fer, is_sabado_sem_escala=is_sab,
                )

                data["registros"][fid][data_str] = {
                    "funcionario_id":   func_id,
                    "data":             data_str,
                    "entrada":          entrada,
                    "inicio_intervalo": ini_int,
                    "fim_intervalo":    fim_int,
                    "saida":            saida,
                    "total_min":        calcs["total_min"],
                    "previsto_min":     calcs["previsto_min"],
                    "saldo_min":        calcs["saldo_min"],
                    "noturno_min":      calcs["noturno_min"],
                    "feriado":          int(is_fer),
                    "dia_semana":       py_wd,
                    "fonte":            "json_import",
                    "conf_entrada":     1.0, "conf_saida": 1.0,
                    "conf_ini_int":     1.0, "conf_fim_int": 1.0,
                }
                total_regs += 1

    save(data)
    return {
        "ok":           True,
        "funcionarios": total_funcs,
        "registros":    total_regs,
        "msg":          f"Importados {total_funcs} funcionário(s) e {total_regs} registro(s).",
    }
