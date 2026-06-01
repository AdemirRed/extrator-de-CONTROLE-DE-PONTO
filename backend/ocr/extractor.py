"""
Extração do cartão DATAPRINT.

Estratégia:
  1. Detecta a grade da tabela via saturação de cor (grade é colorida)
  2. Define 6 colunas de hora (entre 1ª e última linha vertical) + coluna DIA
  3. Identifica as linhas de dados (espaçamento regular)
  4. Roda PaddleOCR (preferencial) ou Tesseract na imagem ampliada
  5. Mapeia cada texto detectado à sua célula (linha, coluna) pela posição
  6. Usa o número do dia (impresso na coluna DIA) para ancorar a linha
  7. Em cada célula de hora, remove o prefixo do dia (carimbo "DD HH:MM")

Mapeamento de colunas DATAPRINT (ENT SAI ENT SAI ENT SAI):
  col 0 → entrada
  col 1 → inicio_intervalo
  col 2 → fim_intervalo
  col 3 → saida
  col 4,5 → batidas extras (ignoradas)
"""

import re
import logging
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Tesseract (fallback) ────────────────────────────────────────────────────
_TESS_PATHS = [
    r"C:\Users\SCM\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
]
for _p in _TESS_PATHS:
    if Path(_p).exists():
        try:
            import pytesseract as _pt
            _pt.pytesseract.tesseract_cmd = _p
        except ImportError:
            pass
        break

# ── PaddleOCR (preferencial) — instância única em cache ────────────────────
_paddle = None
def _get_paddle():
    global _paddle
    if _paddle is None:
        try:
            from paddleocr import PaddleOCR
            _paddle = PaddleOCR(use_angle_cls=False, lang="en",
                                show_log=False, use_gpu=False)
            logger.info("PaddleOCR carregado")
        except Exception as e:
            logger.warning(f"PaddleOCR indisponível: {e}")
            _paddle = False
    return _paddle if _paddle is not False else None


# ── Utilidades ──────────────────────────────────────────────────────────────

def _group(arr, gap=10):
    if len(arr) == 0:
        return []
    g, cur = [], [arr[0]]
    for x in arr[1:]:
        if x - cur[-1] <= gap:
            cur.append(x)
        else:
            g.append(int(np.mean(cur))); cur = [x]
    g.append(int(np.mean(cur)))
    return g


def _detect_grid(img: np.ndarray):
    """Detecta linhas verticais e horizontais da grade via saturação."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    h, w = sat.shape
    _, binary = cv2.threshold(sat, 60, 255, cv2.THRESH_BINARY)

    # Verticais
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 14))
    vl = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk)
    vp = np.sum(vl, axis=0).astype(float); vp /= (vp.max() + 1)
    v_lines = _group(np.where(vp > 0.35)[0])

    # Horizontais
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 6, 1))
    hl = cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk)
    hp = np.sum(hl, axis=1).astype(float); hp /= (hp.max() + 1)
    h_lines = _group(np.where(hp > 0.35)[0])

    return v_lines, h_lines


def _data_rows(h_lines: list[int], n_expected: int) -> list[tuple[int, int]]:
    """
    A partir das linhas horizontais, identifica as faixas das linhas de dados.
    Retorna lista de (y1, y2) das linhas com espaçamento regular.
    """
    if len(h_lines) < 3:
        return []
    # Calcula espaçamentos
    gaps = [h_lines[i+1] - h_lines[i] for i in range(len(h_lines)-1)]
    # Espaçamento típico de linha de dados = mediana dos gaps menores
    sorted_gaps = sorted(gaps)
    median_gap = sorted_gaps[len(sorted_gaps)//2]

    rows = []
    for i in range(len(h_lines) - 1):
        gap = h_lines[i+1] - h_lines[i]
        # Aceita linhas com gap próximo da mediana (±40%)
        if median_gap * 0.6 <= gap <= median_gap * 1.5:
            rows.append((h_lines[i], h_lines[i+1]))
    return rows


# ── Parsing de horário com âncora de dia ───────────────────────────────────

_FIXES = str.maketrans({"O":"0","o":"0","D":"0","I":"1","l":"1","|":"1",
                        "S":"5","B":"8","Z":"2","G":"6","T":"7"})

def _digits_colon(text: str) -> str:
    return re.sub(r"[^0-9:]", "", text.translate(_FIXES))


def _parse_time_anchored(text: str, known_day: int | None) -> tuple[str | None, float]:
    """
    Extrai HH:MM de um texto de célula que pode conter prefixo de dia.
    Ex: "18 6:58" (dia 18) → 06:58.  Usa known_day para remover o prefixo.
    """
    c = _digits_colon(text)
    if not c:
        return None, 0.0

    # Remove prefixo do dia se presente (ex.: "18..." com known_day=18)
    if known_day is not None:
        dstr = str(known_day)
        if c.startswith(dstr) and len(c) > len(dstr):
            c = c[len(dstr):]

    # Caso com ":" → HH:MM
    m = re.search(r"(\d{1,2}):(\d{2})", c)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}", 0.90

    # Sem ":" — só dígitos
    digs = c.replace(":", "")
    # 4 dígitos = HHMM
    if len(digs) == 4:
        h, mn = int(digs[:2]), int(digs[2:])
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}", 0.78
    # 3 dígitos = HMM
    if len(digs) == 3:
        h, mn = int(digs[0]), int(digs[1:])
        if 0 <= mn <= 59:
            return f"0{h}:{mn:02d}", 0.72
    return None, 0.0


def _parse_day(text: str) -> int | None:
    c = re.sub(r"[^0-9]", "", text.translate(_FIXES))
    if c:
        # pega os 2 primeiros dígitos como candidato a dia
        for cand in (c[:2], c[:1]):
            if cand:
                n = int(cand)
                if 1 <= n <= 31:
                    return n
    return None


# ── OCR de boxes (PaddleOCR ou Tesseract) ──────────────────────────────────

def _ocr_boxes(img: np.ndarray) -> list[dict]:
    """
    Retorna lista de {text, conf, cx, cy} de toda a imagem.
    Usa PaddleOCR se disponível, senão Tesseract.
    """
    paddle = _get_paddle()
    if paddle:
        try:
            res = paddle.ocr(img, cls=False)
            boxes = []
            if res and res[0]:
                for line in res[0]:
                    bbox, (txt, conf) = line
                    cx = sum(p[0] for p in bbox) / 4
                    cy = sum(p[1] for p in bbox) / 4
                    boxes.append({"text": txt, "conf": float(conf),
                                   "cx": cx, "cy": cy})
            return boxes
        except Exception as e:
            logger.error(f"PaddleOCR erro: {e}")

    # Fallback Tesseract
    try:
        import pytesseract
        data = pytesseract.image_to_data(
            img, lang="eng", config="--psm 6 --oem 3",
            output_type=pytesseract.Output.DICT,
        )
        boxes = []
        for i, txt in enumerate(data["text"]):
            txt = txt.strip()
            if not txt:
                continue
            conf = max(0.0, float(data["conf"][i]) / 100.0)
            cx = data["left"][i] + data["width"][i] / 2
            cy = data["top"][i] + data["height"][i] / 2
            boxes.append({"text": txt, "conf": conf, "cx": cx, "cy": cy})
        return boxes
    except Exception as e:
        logger.error(f"Tesseract erro: {e}")
        return []


# ── Extração principal ──────────────────────────────────────────────────────

def extract_card_structured(
    img: np.ndarray,
    rows_roi=None,
    face: int = 1,
    conf_minima: float = 0.40,
) -> list[dict]:
    """Extrai horários da face do cartão DATAPRINT usando grade + OCR."""

    n_dias = 15 if face == 1 else 16
    dia_base = 1 if face == 1 else 16

    # 1. Detecta a grade
    v_lines, h_lines = _detect_grid(img)
    if len(v_lines) < 2:
        logger.warning("Grade não detectada — usando fallback")
        return _fallback_text(img, face)

    # 2. Define as 6 colunas de hora + coluna DIA
    x_left, x_right = v_lines[0], v_lines[-1]
    col_w = (x_right - x_left) / 6
    # Coluna DIA: da margem esquerda até x_left
    dia_x1, dia_x2 = max(0, x_left - 130), x_left

    # 3. Linhas de dados
    rows = _data_rows(h_lines, n_dias)
    if len(rows) < 3:
        logger.warning("Linhas de dados não detectadas — usando fallback")
        return _fallback_text(img, face)

    # 4. OCR da imagem inteira (ampliada para precisão)
    h0, w0 = img.shape[:2]
    scale = max(1.0, 1600 / w0)
    big = cv2.resize(img, (int(w0*scale), int(h0*scale)), interpolation=cv2.INTER_CUBIC)
    boxes = _ocr_boxes(big)
    # normaliza coordenadas de volta à escala original
    for b in boxes:
        b["cx"] /= scale
        b["cy"] /= scale

    # 5. Para cada linha de dados, encontra o dia e mapeia os horários
    records = []
    expected = set(range(dia_base, dia_base + n_dias))

    for (y1, y2) in rows:
        ymid = (y1 + y2) / 2
        # boxes dentro desta linha
        row_boxes = [b for b in boxes if y1 - 5 <= b["cy"] <= y2 + 5]
        if not row_boxes:
            continue

        # Descobre o dia: box na coluna DIA
        day = None
        for b in row_boxes:
            if dia_x1 <= b["cx"] <= dia_x2:
                d = _parse_day(b["text"])
                if d in expected:
                    day = d
                    break
        # fallback: usa índice da linha
        if day is None:
            idx = rows.index((y1, y2))
            day = dia_base + idx
            if day not in expected:
                continue

        # Coleta horários da linha, na ordem da esquerda para a direita.
        # Mapeia pela ORDEM (1º=entrada, 2º=ini, 3º=fim, 4º=saida) — isso
        # lida com colunas esparsas/vazias melhor que índice fixo.
        timed = []  # (x, time, conf)
        for b in row_boxes:
            if b["cx"] < x_left - 20 or b["cx"] > x_right + 40:
                continue
            t, tc = _parse_time_anchored(b["text"], day)
            if t:
                timed.append((b["cx"], t, round(tc * b["conf"], 3)))
        timed.sort(key=lambda x: x[0])

        # Remove duplicatas adjacentes (mesma hora detectada 2x)
        dedup = []
        for x, t, c in timed:
            if dedup and dedup[-1][1] == t:
                continue
            dedup.append((x, t, c))

        campos = ["entrada", "inicio_intervalo", "fim_intervalo", "saida"]
        rec = {"dia": day}
        for i, campo in enumerate(campos):
            if i < len(dedup):
                rec[campo] = {"value": dedup[i][1], "conf": dedup[i][2]}
            else:
                rec[campo] = {"value": None, "conf": 0.0}

        if any(rec[c]["value"] for c in campos):
            records.append(rec)

    # Remove dias duplicados (mantém o com mais campos)
    by_day = {}
    for r in records:
        d = r["dia"]
        filled = sum(1 for c in ["entrada","inicio_intervalo","fim_intervalo","saida"]
                     if r[c]["value"])
        if d not in by_day or filled > by_day[d]["_filled"]:
            r["_filled"] = filled
            by_day[d] = r
    result = []
    for d in sorted(by_day):
        r = by_day[d]
        r.pop("_filled", None)
        result.append(r)

    if not result:
        return _fallback_text(img, face)
    return result


# ── Fallback por texto (quando grade falha) ────────────────────────────────

def _fallback_text(img: np.ndarray, face: int) -> list[dict]:
    """Fallback: OCR de linhas e agrupamento por padrão DDHH:MM."""
    h0, w0 = img.shape[:2]
    scale = max(1.0, 1600 / w0)
    big = cv2.resize(img, (int(w0*scale), int(h0*scale)), interpolation=cv2.INTER_CUBIC)
    boxes = _ocr_boxes(big)

    expected = set(range(1, 16)) if face == 1 else set(range(16, 32))

    # Agrupa boxes por linha (cy)
    boxes.sort(key=lambda b: b["cy"])
    lines, cur = [], []
    for b in boxes:
        if cur and abs(b["cy"] - cur[-1]["cy"]) > 25 * scale:
            lines.append(cur); cur = []
        cur.append(b)
    if cur:
        lines.append(cur)

    records = []
    for line in lines:
        line.sort(key=lambda b: b["cx"])
        text = " ".join(b["text"] for b in line)
        c = _digits_colon(text)
        # dia dominante
        day = None
        for m in re.finditer(r"(?<!\d)(\d{1,2})(?!\d)", re.sub(r"\d{1,2}:\d{2}", " ", c)):
            n = int(m.group(1))
            if n in expected:
                day = n; break
        if day is None:
            continue
        # horários em ordem
        times = []
        for m in re.finditer(r"(\d{1,2}):(\d{2})", c):
            h, mn = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mn <= 59:
                times.append(f"{h:02d}:{mn:02d}")
        if not times:
            continue
        campos = ["entrada","inicio_intervalo","fim_intervalo","saida"]
        rec = {"dia": day}
        for i, campo in enumerate(campos):
            rec[campo] = {"value": times[i], "conf": 0.70} if i < len(times) \
                         else {"value": None, "conf": 0.0}
        records.append(rec)

    by_day = {r["dia"]: r for r in records}
    return [by_day[d] for d in sorted(by_day)]
