"""
Cálculos de horas: total, saldo, noturno, extras.
"""

from datetime import datetime, date, timedelta
import calendar


def parse_time(t: str | None) -> int | None:
    """Converte 'HH:MM' em minutos desde meia-noite. Retorna None se inválido."""
    if not t or not isinstance(t, str):
        return None
    t = t.strip()
    parts = t.split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h * 60 + m
    except ValueError:
        pass
    return None


def minutes_to_str(minutes: int | None) -> str:
    """Converte minutos em 'HH:MM'. Suporta negativos."""
    if minutes is None:
        return "—"
    neg = minutes < 0
    minutes = abs(minutes)
    h, m = divmod(minutes, 60)
    s = f"{h:02d}:{m:02d}"
    return f"-{s}" if neg else s


def calc_dia(
    entrada: str | None,
    inicio_int: str | None,
    fim_int: str | None,
    saida: str | None,
    sched_inicio: str = "07:00",
    sched_fim: str = "17:00",
    sched_int_ini: str = "12:00",
    sched_int_fim: str = "13:00",
    noturno_inicio: str = "22:00",
    is_feriado: bool = False,
    is_sabado_sem_escala: bool = False,
) -> dict:
    """
    Calcula total, previsto, saldo e noturno para um dia.
    Retorna dict com todos os campos em minutos + strings formatadas.
    """
    ini = parse_time(entrada)
    fim = parse_time(saida)
    result = {
        "total_min": None, "previsto_min": None,
        "saldo_min": None,  "noturno_min": None,
        "total_str": "—", "previsto_str": "—",
        "saldo_str": "—",  "noturno_str": "—",
    }

    if ini is None or fim is None or fim <= ini:
        return result

    ii = parse_time(inicio_int)
    fi = parse_time(fim_int)
    # Fallback para o intervalo da escala APENAS em dias normais.
    # Em feriado ou sábado sem escala, só desconta intervalo se o
    # funcionário realmente bateu o ponto do almoço (evita almoço fantasma).
    if not is_feriado and not is_sabado_sem_escala:
        if ii is None:
            ii = parse_time(sched_int_ini)
        if fi is None:
            fi = parse_time(sched_int_fim)

    # Total descontando intervalo
    if ii is not None and fi is not None and ii >= ini and fi <= fim and fi > ii:
        total = (ii - ini) + (fim - fi)
    else:
        total = fim - ini

    # Adicional noturno (após 22h)
    ns = parse_time(noturno_inicio) or 22 * 60
    noturno = max(0, fim - max(ini, ns)) if fim > ns else 0

    # Previsto
    if is_feriado or is_sabado_sem_escala:
        previsto = 0
        saldo = total
    else:
        ps = parse_time(sched_inicio)
        pf = parse_time(sched_fim)
        pi = parse_time(sched_int_ini)
        pfi = parse_time(sched_int_fim)
        if ps and pf and pf > ps:
            int_previsto = (pfi - pi) if (pi and pfi and pfi > pi) else 60
            previsto = (pf - ps) - int_previsto
        else:
            previsto = 0
        saldo = total - previsto if previsto > 0 else 0

    result.update({
        "total_min":    total,
        "previsto_min": previsto,
        "saldo_min":    saldo,
        "noturno_min":  noturno if noturno > 0 else None,
        "total_str":    minutes_to_str(total),
        "previsto_str": minutes_to_str(previsto) if previsto > 0 else "—",
        "saldo_str":    (("+" if saldo >= 0 else "") + minutes_to_str(saldo)),
        "noturno_str":  minutes_to_str(noturno) if noturno > 0 else "—",
    })
    return result


def get_weekday(data_str: str) -> int:
    """Retorna dia da semana: 0=segunda … 6=domingo."""
    try:
        d = datetime.strptime(data_str, "%Y-%m-%d")
        return d.weekday()  # 0=seg, 6=dom
    except ValueError:
        return -1


def dias_no_mes(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]
