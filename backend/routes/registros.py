"""Registros de ponto — armazenamento JSON."""

import calendar
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from backend.storage import load, save
from backend.utils.calculations import calc_dia, get_weekday

router = APIRouter(prefix="/api/registros", tags=["registros"])


class RegistroIn(BaseModel):
    funcionario_id:   int
    data:             str   # YYYY-MM-DD
    entrada:          Optional[str] = None
    inicio_intervalo: Optional[str] = None
    fim_intervalo:    Optional[str] = None
    saida:            Optional[str] = None
    feriado:          Optional[int] = 0
    conf_entrada:     Optional[float] = 1.0
    conf_saida:       Optional[float] = 1.0
    conf_ini_int:     Optional[float] = 1.0
    conf_fim_int:     Optional[float] = 1.0
    fonte:            Optional[str] = "manual"


def _get_func(data, fid):
    f = next((f for f in data["funcionarios"] if f["id"] == fid and f.get("ativo", True)), None)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado")
    return f


def _sched_do_dia(cfg, data_str):
    """
    Retorna (entrada, saida, int_ini, int_fim, ativo) da escala global
    para o dia-da-semana da data. Usa config['schedule'] (chave JS getDay).
    """
    py_wd = get_weekday(data_str)        # 0=Seg .. 6=Dom
    js_wd = (py_wd + 1) % 7              # 0=Dom .. 6=Sáb
    schedule = cfg.get("schedule", {})
    s = schedule.get(str(js_wd))
    if s and s.get("ativo"):
        return (s.get("entrada") or "07:00", s.get("saida") or "17:30",
                s.get("intInicio") or "11:30", s.get("intFim") or "13:00", True)
    return ("07:00", "17:30", "11:30", "13:00", False)


def _compute(data, reg: RegistroIn) -> dict:
    func     = _get_func(data, reg.funcionario_id)
    cfg      = data.get("config", {})
    feriado  = bool(reg.feriado) or (reg.data in data.get("feriados", {}))
    dw       = get_weekday(reg.data)   # 0=seg … 6=dom

    s_ent, s_sai, s_ini, s_fim, ativo = _sched_do_dia(cfg, reg.data)
    # Dia sem escala ativa (sáb/dom) → todas as horas contam como extra
    sem_escala = not ativo

    calcs = calc_dia(
        entrada              = reg.entrada,
        inicio_int           = reg.inicio_intervalo,
        fim_int              = reg.fim_intervalo,
        saida                = reg.saida,
        sched_inicio         = s_ent,
        sched_fim            = s_sai,
        sched_int_ini        = s_ini,
        sched_int_fim        = s_fim,
        noturno_inicio       = cfg.get("noturno_inicio", "22:00"),
        is_feriado           = feriado,
        is_sabado_sem_escala = sem_escala,
    )

    rec = {
        "funcionario_id":   reg.funcionario_id,
        "data":             reg.data,
        "entrada":          reg.entrada,
        "inicio_intervalo": reg.inicio_intervalo,
        "fim_intervalo":    reg.fim_intervalo,
        "saida":            reg.saida,
        "total_min":        calcs["total_min"],
        "previsto_min":     calcs["previsto_min"],
        "saldo_min":        calcs["saldo_min"],
        "noturno_min":      calcs["noturno_min"],
        "feriado":          int(feriado),
        "conf_entrada":     reg.conf_entrada,
        "conf_saida":       reg.conf_saida,
        "conf_ini_int":     reg.conf_ini_int,
        "conf_fim_int":     reg.conf_fim_int,
        "fonte":            reg.fonte,
        "dia_semana":       dw,
    }
    return rec


def _store(data, rec: dict):
    fid  = str(rec["funcionario_id"])
    data_str = rec["data"]
    if fid not in data["registros"]:
        data["registros"][fid] = {}
    data["registros"][fid][data_str] = rec


# ── endpoints ─────────────────────────────────────────────────────────────

@router.get("/mes")
def listar_mes(
    funcionario_id: int = Query(...),
    ano: int = Query(...),
    mes: int = Query(...),
):
    data       = load()
    func       = _get_func(data, funcionario_id)
    regs       = data["registros"].get(str(funcionario_id), {})
    feriados   = data.get("feriados", {})
    total_dias = calendar.monthrange(ano, mes)[1]

    result = []
    for d in range(1, total_dias + 1):
        data_str = f"{ano}-{mes:02d}-{d:02d}"
        dw       = get_weekday(data_str)
        feriado  = data_str in feriados

        if data_str in regs:
            rec = dict(regs[data_str])
        else:
            rec = {
                "funcionario_id": funcionario_id, "data": data_str,
                "entrada": None, "inicio_intervalo": None,
                "fim_intervalo": None, "saida": None,
                "total_min": None, "previsto_min": None,
                "saldo_min": None, "noturno_min": None,
                "feriado": int(feriado), "fonte": None,
                "conf_entrada": 1.0, "conf_saida": 1.0,
                "conf_ini_int": 1.0, "conf_fim_int": 1.0,
            }

        rec["dia_semana"] = dw
        rec["is_feriado"] = feriado
        rec["is_fds"]     = dw >= 5
        result.append(rec)

    return result


@router.post("", status_code=201)
def salvar(reg: RegistroIn):
    data = load()
    rec  = _compute(data, reg)
    _store(data, rec)
    save(data)
    return rec


@router.post("/lote")
def salvar_lote(registros: list[RegistroIn]):
    data = load()
    for reg in registros:
        rec = _compute(data, reg)
        _store(data, rec)
    save(data)
    return {"ok": True, "saved": len(registros)}


@router.delete("/{funcionario_id}/mes")
def limpar_mes(
    funcionario_id: int,
    ano: int = Query(...),
    mes: int = Query(...),
):
    data   = load()
    fid    = str(funcionario_id)
    prefix = f"{ano}-{mes:02d}-"
    regs   = data["registros"].get(fid, {})
    to_del = [k for k in regs if k.startswith(prefix)]
    for k in to_del:
        del regs[k]
    save(data)
    return {"ok": True, "deleted": len(to_del)}


@router.get("/dashboard")
def dashboard(ano: int = Query(...), mes: int = Query(...)):
    data   = load()
    prefix = f"{ano}-{mes:02d}-"
    result = []
    for func in data["funcionarios"]:
        if not func.get("ativo", True):
            continue
        regs = data["registros"].get(str(func["id"]), {})
        total_h = saldo = noturno = previsto = dias = 0
        for k, r in regs.items():
            if not k.startswith(prefix):
                continue
            if r.get("total_min") is not None:
                total_h  += r.get("total_min")  or 0
                saldo    += r.get("saldo_min")   or 0
                noturno  += r.get("noturno_min") or 0
                previsto += r.get("previsto_min") or 0
                dias     += 1
        result.append({
            "id":               func["id"],
            "nome":             func["nome"],
            "total_h":          total_h,
            "saldo":            saldo,
            "noturno":          noturno,
            "previsto":         previsto,
            "dias_trabalhados": dias,
        })
    return result


@router.get("/anual")
def anual(funcionario_id: int = Query(...), ano: int = Query(...)):
    """Retorna os 12 meses agregados de um funcionário no ano."""
    data = load()
    func = _get_func(data, funcionario_id)
    regs = data["registros"].get(str(funcionario_id), {})

    meses = []
    for mes in range(1, 13):
        prefix = f"{ano}-{mes:02d}-"
        sumH = sumN = sumE = sumNot = diasTrab = diasFer = diasSab = 0
        for k, r in regs.items():
            if not k.startswith(prefix):
                continue
            if r.get("total_min") is None:
                continue
            sumH    += r.get("total_min")    or 0
            sumN    += r.get("previsto_min") or 0
            sumE    += r.get("saldo_min")    or 0
            sumNot  += r.get("noturno_min")  or 0
            diasTrab += 1
            if r.get("feriado"):
                diasFer += 1
            # dia_semana py: 5 = sábado
            if r.get("dia_semana") == 5 and (r.get("previsto_min") or 0) == 0:
                diasSab += 1
        meses.append({
            "mes": mes, "sumH": sumH, "sumN": sumN, "sumE": sumE,
            "sumNot": sumNot, "diasTrab": diasTrab,
            "diasFer": diasFer, "diasSab": diasSab,
        })

    return {"id": func["id"], "nome": func["nome"], "ano": ano, "meses": meses}
