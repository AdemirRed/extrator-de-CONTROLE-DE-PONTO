"""
Integração com LLM (Ollama Cloud / API compatível com OpenAI).

Endpoints:
  GET  /api/ia/config    → retorna config da IA (sem expor a key inteira)
  POST /api/ia/config    → salva base_url / api_key / model
  GET  /api/ia/modelos   → lista modelos disponíveis no provedor
  POST /api/ia/testar    → testa a conexão
  POST /api/ia/perguntar → pergunta em linguagem natural sobre os dados do ponto
"""

import json
import base64
import re
import urllib.request
import urllib.error
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from backend.storage import load, save
from backend.utils.calculations import minutes_to_str, get_weekday

router = APIRouter(prefix="/api/ia", tags=["ia"])

DEFAULT_BASE = "https://ollama.com/v1"


# ── Config da IA ────────────────────────────────────────────────────────────

class IAConfig(BaseModel):
    base_url: Optional[str] = DEFAULT_BASE
    api_key:  Optional[str] = ""
    model:    Optional[str] = ""


def _ia_cfg(data) -> dict:
    cfg = data.get("config", {})
    return {
        "base_url": cfg.get("ia_base_url") or DEFAULT_BASE,
        "api_key":  cfg.get("ia_api_key") or "",
        "model":    cfg.get("ia_model") or "",
    }


@router.get("/config")
def get_config():
    ia = _ia_cfg(load())
    key = ia["api_key"]
    return {
        "base_url":  ia["base_url"],
        "model":     ia["model"],
        "has_key":   bool(key),
        "key_mask":  (key[:6] + "…" + key[-4:]) if len(key) > 12 else ("•" * len(key)),
    }


@router.post("/config")
def set_config(c: IAConfig):
    data = load()
    cfg = data.setdefault("config", {})
    cfg["ia_base_url"] = c.base_url or DEFAULT_BASE
    if c.api_key is not None and c.api_key != "":
        cfg["ia_api_key"] = c.api_key           # só sobrescreve se enviado
    cfg["ia_model"] = c.model or ""
    save(data)
    return {"ok": True}


# ── Chamadas HTTP ao provedor ───────────────────────────────────────────────

def _http(url: str, method: str, key: str, payload: dict | None = None, timeout=60):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise HTTPException(e.code, f"Provedor retornou {e.code}: {detail}")
    except Exception as e:
        raise HTTPException(502, f"Falha ao conectar no provedor de IA: {e}")


@router.get("/modelos")
def listar_modelos():
    ia = _ia_cfg(load())
    if not ia["api_key"]:
        raise HTTPException(400, "Configure a API key primeiro")
    res = _http(f"{ia['base_url'].rstrip('/')}/models", "GET", ia["api_key"], timeout=20)
    modelos = [m.get("id") for m in res.get("data", []) if m.get("id")]
    return {"modelos": modelos}


@router.post("/testar")
def testar():
    ia = _ia_cfg(load())
    if not ia["api_key"]:
        raise HTTPException(400, "Configure a API key primeiro")
    if not ia["model"]:
        raise HTTPException(400, "Escolha um modelo primeiro")
    res = _http(
        f"{ia['base_url'].rstrip('/')}/chat/completions", "POST", ia["api_key"],
        {"model": ia["model"],
         "messages": [{"role": "user", "content": "Responda apenas: OK"}],
         "max_tokens": 10},
        timeout=30,
    )
    txt = res.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"ok": True, "resposta": txt.strip()}


# ── Contexto a partir dos dados do ponto ────────────────────────────────────

MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]


DIAS_NOME = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]  # get_weekday: 0=Seg..6=Dom

# Limite de caracteres por bloco enviado à IA (~4 chars/token).
# Acima disso, fraciona em vários blocos e consolida no final.
CHUNK_CHARS = 14000


def _header(data, ano: int) -> str:
    """Cabeçalho com escala/regras (vai em todos os blocos)."""
    cfg = data.get("config", {})
    sched = cfg.get("schedule", {})
    linhas = [f"DADOS DE PONTO — ANO {ano}",
              "Formato dos dias: DD/MM (DiaSemana): entrada-saida | total | saldo | noturno",
              "saldo positivo = horas extras (serão); negativo = horas devidas.",
              f"Adicional noturno a partir de: {cfg.get('noturno_inicio','22:00')}",
              "Escala semanal prevista:"]
    dnome = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]
    for wd in range(7):
        s = sched.get(str(wd), {})
        if s.get("ativo"):
            linhas.append(f"  {dnome[wd]}: {s.get('entrada')}–{s.get('saida')} (almoço {s.get('intInicio')}–{s.get('intFim')})")
    return "\n".join(linhas)


def _employee_block(data, func, ano: int) -> str:
    """Bloco com o detalhe diário de UM funcionário."""
    fid = str(func["id"])
    regs = data.get("registros", {}).get(fid, {})
    feriados = data.get("feriados", {})
    linhas = [f"════ FUNCIONÁRIO: {func['nome']} ════"]
    tot_saldo = tot_h = tot_not = tot_dias = 0
    for mes in range(1, 13):
        prefix = f"{ano}-{mes:02d}-"
        dias_com = sorted([k for k in regs if k.startswith(prefix) and regs[k].get("total_min") is not None])
        if not dias_com:
            continue
        sH = sE = sNot = 0
        linhas.append(f"  {MESES[mes-1]}/{ano}:")
        for k in dias_com:
            r = regs[k]
            wd = get_weekday(k)
            dsw = DIAS_NOME[wd] if 0 <= wd <= 6 else "?"
            fer = " [FERIADO]" if k in feriados else ""
            tot = r.get("total_min") or 0; sal = r.get("saldo_min") or 0; noturno = r.get("noturno_min") or 0
            linhas.append(
                f"    {k[-2:]}/{mes:02d} ({dsw}){fer}: {r.get('entrada') or '--'}-{r.get('saida') or '--'} | "
                f"total {minutes_to_str(tot)} | saldo {('+' if sal>=0 else '')}{minutes_to_str(sal)}"
                + (f" | noturno {minutes_to_str(noturno)}" if noturno else "")
            )
            sH += tot; sE += sal; sNot += noturno
        linhas.append(f"    → Subtotal {MESES[mes-1]}: {len(dias_com)} dias, total {minutes_to_str(sH)}, "
                      f"saldo {('+' if sE>=0 else '')}{minutes_to_str(sE)}, noturno {minutes_to_str(sNot)}")
        tot_saldo += sE; tot_h += sH; tot_not += sNot; tot_dias += len(dias_com)
    linhas.append(f"  TOTAL ANO {func['nome']}: {tot_dias} dias, total {minutes_to_str(tot_h)}, "
                  f"saldo {('+' if tot_saldo>=0 else '')}{minutes_to_str(tot_saldo)}, noturno {minutes_to_str(tot_not)}")
    return "\n".join(linhas)


def _chunk_blocks(blocks: list[str], header: str) -> list[str]:
    """Agrupa blocos de funcionários em pedaços que respeitam CHUNK_CHARS."""
    chunks, atual, tam = [], [], len(header)
    for b in blocks:
        if atual and tam + len(b) > CHUNK_CHARS:
            chunks.append(header + "\n\n" + "\n\n".join(atual))
            atual, tam = [], len(header)
        atual.append(b); tam += len(b) + 2
    if atual:
        chunks.append(header + "\n\n" + "\n\n".join(atual))
    return chunks


def _build_context(data, ano: int) -> str:
    """Contexto completo (usado quando cabe em um único bloco)."""
    blocks = [_employee_block(data, f, ano) for f in data.get("funcionarios", []) if f.get("ativo", True)]
    return _header(data, ano) + "\n\n" + "\n\n".join(blocks)


class Pergunta(BaseModel):
    pergunta: str
    ano: Optional[int] = None


_REGRAS = (
    "Os dados trazem o DETALHE DIÁRIO de cada funcionário, com o dia da semana entre parênteses "
    "(Seg, Ter, Qua, Qui, Sex, Sáb, Dom). Você PODE filtrar e somar por dia da semana, período, "
    "feriado, etc. Horários no formato HH:MM. 'saldo' positivo = horas extras (serão); negativo = devidas. "
    "Ao somar horas, mostre o resultado em HH:MM."
)


def _extract_msg(res) -> tuple[str, str]:
    """
    Extrai o texto da resposta de forma robusta.
    Modelos de raciocínio (gpt-oss) às vezes deixam 'content' vazio e
    colocam o texto em 'reasoning'/'reasoning_content', ou usam lista de partes.
    Retorna (texto, finish_reason).
    """
    ch = (res.get("choices") or [{}])[0]
    msg = ch.get("message", {}) or {}
    content = msg.get("content")
    if isinstance(content, list):
        content = "".join(
            (part.get("text", "") if isinstance(part, dict) else str(part))
            for part in content
        )
    content = (content or "").strip()
    if not content:
        for campo in ("reasoning_content", "reasoning"):
            v = msg.get(campo)
            if isinstance(v, str) and v.strip():
                content = v.strip()
                break
    return content, ch.get("finish_reason", "")


def _chat(ia, system, user, max_tokens=3000):
    payload = {
        "model": ia["model"],
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    res = _http(f"{ia['base_url'].rstrip('/')}/chat/completions", "POST", ia["api_key"],
                payload, timeout=180)
    texto, finish = _extract_msg(res)

    # Se truncou no raciocínio (content vazio + finish 'length'), tenta de novo
    # pedindo resposta direta e com mais espaço.
    if not texto and finish == "length":
        payload["max_tokens"] = min(4096, max_tokens + 1500)
        payload["messages"][0]["content"] = system + (
            "\n\nIMPORTANTE: responda DIRETO e curto, sem raciocínio extenso."
        )
        res2 = _http(f"{ia['base_url'].rstrip('/')}/chat/completions", "POST", ia["api_key"],
                     payload, timeout=180)
        texto, finish = _extract_msg(res2)
    return texto


@router.post("/perguntar")
def perguntar(p: Pergunta):
    data = load()
    ia = _ia_cfg(data)
    if not ia["api_key"]:
        raise HTTPException(400, "Configure a API key da IA nas Configurações")
    if not ia["model"]:
        raise HTTPException(400, "Escolha um modelo da IA nas Configurações")

    from datetime import datetime
    ano = p.ano or datetime.now().year

    header = _header(data, ano)
    blocks = [_employee_block(data, f, ano)
              for f in data.get("funcionarios", []) if f.get("ativo", True)]
    if not blocks:
        return {"ok": True, "resposta": "Não há funcionários cadastrados."}

    chunks = _chunk_blocks(blocks, header)

    # ── Caso simples: cabe em 1 bloco → resposta direta ──
    if len(chunks) == 1:
        system = ("Você é um assistente de RH especializado em controle de ponto. "
                  "Responda em PT-BR, objetivo, usando SOMENTE os dados abaixo. " + _REGRAS +
                  " Se a informação não estiver nos dados, diga que não há registro.\n\n" + chunks[0])
        resp = _chat(ia, system, p.pergunta, max_tokens=3500)
        return {"ok": True, "resposta": resp or "(sem resposta — tente reformular a pergunta)", "blocos": 1}

    # ── Map: extrai fatos relevantes de cada bloco ──
    parciais = []
    for i, ch in enumerate(chunks):
        sys_map = ("Você é um assistente de RH. Abaixo está uma PARTE dos dados de ponto "
                   f"(bloco {i+1} de {len(chunks)}). " + _REGRAS +
                   " Extraia APENAS os fatos/números relevantes para responder à pergunta do usuário. "
                   "Seja conciso e mostre os cálculos parciais. "
                   "Se nada neste bloco for relevante, responda exatamente 'SEM DADOS RELEVANTES'.\n\n" + ch)
        try:
            r = _chat(ia, sys_map, p.pergunta, max_tokens=2500)
        except HTTPException:
            r = "SEM DADOS RELEVANTES"
        if r and "SEM DADOS RELEVANTES" not in r.upper():
            parciais.append(f"[Bloco {i+1}]\n{r}")

    if not parciais:
        return {"ok": True, "resposta": "Não encontrei dados relevantes para essa pergunta.",
                "blocos": len(chunks)}

    # ── Reduce: consolida tudo numa resposta final única ──
    sys_red = ("Você é um assistente de RH. Abaixo estão respostas PARCIAIS extraídas de vários "
               "blocos dos dados de ponto. Consolide em UMA resposta final, completa e objetiva, "
               "em PT-BR, para a pergunta do usuário. Some/ordene/compare o que for necessário e "
               "mostre o resultado final em HH:MM quando envolver horas. Não mencione 'blocos'.\n\n"
               "RESPOSTAS PARCIAIS:\n" + "\n\n".join(parciais))
    final = _chat(ia, sys_red, p.pergunta, max_tokens=3500)
    return {"ok": True, "resposta": final or "(sem resposta — tente reformular a pergunta)", "blocos": len(chunks)}


# ── LEITURA DE CARTÃO VIA IA (visão) — experimental ─────────────────────────

def _ler_face_ia(ia, img_bytes: bytes, ext: str, face: int) -> list[dict]:
    """Envia a imagem do cartão para o modelo (com visão) e pede os horários em JSON."""
    mime = "image/png" if ext.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(img_bytes).decode()
    dia_base = 1 if face == 1 else 16
    instr = (
        "Esta é a FACE de um cartão de ponto DATAPRINT. As colunas são: "
        "DIA | ENT | SAI | ENT | SAI | ENT | SAI. Mapeie a 1ª ENT=entrada, "
        "1ª SAI=inicio_intervalo, 2ª ENT=fim_intervalo, 2ª SAI=saida. "
        f"Esta face cobre os dias começando em {dia_base}. "
        "Extraia os horários de CADA linha que tiver marcação. "
        "Responda APENAS com um JSON (sem texto extra), no formato:\n"
        '[{"dia":N,"entrada":"HH:MM","inicio_intervalo":"HH:MM","fim_intervalo":"HH:MM","saida":"HH:MM"}]\n'
        "Use null para campos vazios. Horário 24h."
    )
    payload = {
        "model": ia["model"],
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": instr},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        "temperature": 0.1, "max_tokens": 3000,
    }
    res = _http(f"{ia['base_url'].rstrip('/')}/chat/completions", "POST", ia["api_key"],
                payload, timeout=180)
    txt, _ = _extract_msg(res)
    # extrai o JSON da resposta
    m = re.search(r"\[.*\]", txt, re.DOTALL)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    out = []
    for r in arr:
        if not isinstance(r, dict):
            continue
        def _v(k):
            x = r.get(k)
            return x if (isinstance(x, str) and re.match(r"^\d{1,2}:\d{2}$", x)) else None
        rec = {
            "dia": r.get("dia"),
            "entrada":          {"value": _v("entrada"),          "conf": 0.50, "low_conf": True},
            "inicio_intervalo": {"value": _v("inicio_intervalo"), "conf": 0.50, "low_conf": True},
            "fim_intervalo":    {"value": _v("fim_intervalo"),    "conf": 0.50, "low_conf": True},
            "saida":            {"value": _v("saida"),            "conf": 0.50, "low_conf": True},
        }
        if rec["dia"] and (rec["entrada"]["value"] or rec["saida"]["value"]):
            out.append(rec)
    return out


@router.post("/ler-cartao")
async def ler_cartao(
    file:  UploadFile = File(...),
    file2: Optional[UploadFile] = File(None),
    funcionario_id: Optional[int] = Form(None),
):
    """Tenta ler o cartão usando o LLM (visão). Experimental — requer modelo com visão."""
    ia = _ia_cfg(load())
    if not ia["api_key"] or not ia["model"]:
        raise HTTPException(400, "Configure a API key e o modelo da IA em Configurações")

    import os
    regs = []
    try:
        ext1 = os.path.splitext(file.filename or "img.jpg")[1] or ".jpg"
        regs += _ler_face_ia(ia, await file.read(), ext1, face=1)
        if file2 and file2.filename:
            ext2 = os.path.splitext(file2.filename)[1] or ".jpg"
            regs += _ler_face_ia(ia, await file2.read(), ext2, face=2)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Falha ao ler com IA: {e}")

    if not regs:
        return {"ok": False, "engine_used": "IA (LLM)", "registros": [],
                "msg": "A IA não conseguiu extrair horários. O modelo precisa ter visão "
                       "(ex.: llama3.2-vision). Use o OCR tradicional."}
    return {"ok": True, "engine_used": "IA (LLM)", "registros": regs,
            "msg": f"IA leu {len(regs)} dia(s) — revise com atenção (baixa confiança)."}
