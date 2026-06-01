"""
Detecção de grade DATAPRINT a partir do cartão em branco.

O cartão vazio tem linhas de grade muito claras (sem ruído de carimbos).
Detectamos os X e Y exatos de cada coluna e linha para depois
recortar cada célula do cartão preenchido com precisão.
"""

import json
import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "ocr_templates"
TEMPLATES_DIR.mkdir(exist_ok=True)

TEMPLATE_F1 = TEMPLATES_DIR / "grid_face1.json"
TEMPLATE_F2 = TEMPLATES_DIR / "grid_face2.json"


# ── Detecção de grade ──────────────────────────────────────────────────────

def _to_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()


def _find_lines(binary: np.ndarray, direction: str) -> list[int]:
    """
    Detecta linhas horizontais ou verticais da tabela.
    direction: 'h' ou 'v'
    """
    H, W = binary.shape
    if direction == 'h':
        # Kernel horizontal largo (mínimo 30% da largura)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(W // 3, 40), 1))
        lines  = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        proj   = np.sum(lines, axis=1).astype(float)
    else:
        # Kernel vertical alto (mínimo 10% da altura)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(H // 10, 20)))
        lines  = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        proj   = np.sum(lines, axis=0).astype(float)

    if proj.max() < 1:
        return []

    proj /= proj.max()
    ys = np.where(proj > 0.15)[0].tolist()
    if not ys:
        return []

    # Agrupa pixels próximos → centro de cada linha
    groups, grp = [], [ys[0]]
    for y in ys[1:]:
        if y - grp[-1] <= 4:
            grp.append(y)
        else:
            groups.append(int(np.mean(grp)))
            grp = [y]
    groups.append(int(np.mean(grp)))
    return groups


def detect_grid(img: np.ndarray, face: int) -> dict | None:
    """
    Detecta a grade DATAPRINT de um cartão em branco.

    Returns:
        dict com:
          - col_xs: lista de X (bordas das colunas) normalizados 0.0–1.0
          - row_ys: lista de Y (bordas das linhas) normalizados 0.0–1.0
          - face: 1 ou 2
          - img_w, img_h: dimensões originais (para escalar de volta)
    """
    gray   = _to_gray(img)
    H, W   = gray.shape
    scale  = 2
    big    = cv2.resize(gray, (W * scale, H * scale), interpolation=cv2.INTER_CUBIC)

    # Binariza invertido (linhas = preto no original → branco invertido)
    _, binary = cv2.threshold(big, 200, 255, cv2.THRESH_BINARY_INV)

    h_lines = _find_lines(binary, 'h')
    v_lines = _find_lines(binary, 'v')

    logger.info(f"Template face {face}: {len(h_lines)} linhas H, {len(v_lines)} linhas V")

    if len(h_lines) < 5 or len(v_lines) < 6:
        return None

    # Normaliza para 0.0–1.0 (relativo ao tamanho da imagem)
    H2, W2 = big.shape
    col_xs = [x / W2 for x in v_lines]
    row_ys = [y / H2 for y in h_lines]

    return {
        "face":    face,
        "col_xs":  col_xs,
        "row_ys":  row_ys,
        "img_w":   W,
        "img_h":   H,
        "n_cols":  len(v_lines) - 1,
        "n_rows":  len(h_lines) - 1,
    }


def save_template(grid: dict, face: int):
    path = TEMPLATE_F1 if face == 1 else TEMPLATE_F2
    path.write_text(json.dumps(grid, indent=2), encoding="utf-8")
    logger.info(f"Template face {face} salvo: {path}")


def load_template(face: int) -> dict | None:
    path = TEMPLATE_F1 if face == 1 else TEMPLATE_F2
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── Extração por célula usando template ────────────────────────────────────

def extract_with_template(
    img: np.ndarray,
    template: dict,
    face: int,
) -> list[dict]:
    """
    Recorta cada célula da tabela usando coordenadas do template.
    Roda OCR em cada célula individualmente.

    Mapeamento de colunas (índice):
      0 = DIA  1 = ENT1  2 = SAI1  3 = ENT2  4 = SAI2  5 = ENT3  6 = SAI3  7 = EXTRA
    """
    import pytesseract
    from .extractor import _available_langs, _fix_time

    gray  = _to_gray(img)
    H, W  = gray.shape
    scale = 2
    big   = cv2.resize(gray, (W * scale, H * scale), interpolation=cv2.INTER_CUBIC)

    # CLAHE para melhorar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enh   = clahe.apply(big)
    H2, W2 = enh.shape

    col_xs = [int(x * W2) for x in template["col_xs"]]
    row_ys = [int(y * H2) for y in template["row_ys"]]

    # Filtra linhas que estão dentro da área de dados
    # (pula cabeçalho e footer)
    dia_base  = 1 if face == 1 else 16
    dia_range = range(1, 16) if face == 1 else range(16, 32)
    campos    = ["entrada", "inicio_intervalo", "fim_intervalo", "saida"]

    records = []
    langs   = _available_langs()

    for ri in range(len(row_ys) - 1):
        y1, y2 = row_ys[ri], row_ys[ri + 1]
        row_h  = y2 - y1
        if row_h < 8:
            continue

        # ── Coluna 0: DIA (texto rotacionado 90°) ──
        x_dia_end = col_xs[1] if len(col_xs) > 1 else W2 // 8
        dia_strip = enh[y1:y2, :x_dia_end]

        # Tenta ler o dia (está rotacionado 90° CW no cartão)
        dia_num = None
        for rot_code in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE, None]:
            strip_try = cv2.rotate(dia_strip, rot_code) if rot_code is not None else dia_strip
            # Escala para legibilidade
            sh, sw = strip_try.shape[:2]
            if sw > 0 and sh > 0:
                strip_big = cv2.resize(strip_try, (max(sw*3, 60), max(sh*3, 60)),
                                        interpolation=cv2.INTER_CUBIC)
                txt = pytesseract.image_to_string(
                    strip_big, lang=langs,
                    config="--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789"
                ).strip()
                txt_clean = txt.replace(" ", "").strip()
                if txt_clean.isdigit():
                    n = int(txt_clean)
                    if n in dia_range:
                        dia_num = n
                        break

        if dia_num is None:
            # Fallback: estima o dia pela posição da linha
            idx = ri  # índice da linha de dados (após header)
            est = dia_base + idx - 1  # -1 porque primeiro índice é header
            if est in dia_range:
                dia_num = est

        if dia_num is None:
            continue

        # ── Colunas de tempo: ENT1(1), SAI1(2), ENT2(3), SAI2(4) ──
        rec = {"dia": dia_num}
        for ci, campo in enumerate(campos, start=1):
            if ci >= len(col_xs):
                rec[campo] = {"value": None, "conf": 0.0}
                continue
            x1 = col_xs[ci]
            x2 = col_xs[ci + 1] if ci + 1 < len(col_xs) else W2
            cell = enh[y1:y2, x1:x2]
            if cell.size == 0:
                rec[campo] = {"value": None, "conf": 0.0}
                continue

            # Escala a célula para OCR
            ch, cw = cell.shape[:2]
            cell_big = cv2.resize(cell, (max(cw*4, 80), max(ch*4, 40)),
                                   interpolation=cv2.INTER_CUBIC)

            txt = pytesseract.image_to_string(
                cell_big, lang=langs,
                config="--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789:"
            ).strip()
            txt = _fix_time(txt.strip())

            # Parse do horário
            import re
            m = re.search(r"(\d{1,2}):(\d{2})", txt)
            if not m:
                # Tenta HHMM (sem ":") — ex: "0700"
                d = re.sub(r"[^0-9]", "", txt)
                m2 = re.match(r"^(\d{2})(\d{2})$", d)
                if m2:
                    h_v, mn_v = int(m2.group(1)), int(m2.group(2))
                    if 0 <= h_v <= 23 and 0 <= mn_v <= 59:
                        sanity_conf = 0.72 if 5 <= h_v <= 23 else 0.30
                        rec[campo] = {"value": f"{h_v:02d}:{mn_v:02d}", "conf": sanity_conf}
                        continue
                rec[campo] = {"value": None, "conf": 0.0}
                continue

            h_v, mn_v = int(m.group(1)), int(m.group(2))
            if 0 <= h_v <= 23 and 0 <= mn_v <= 59:
                sanity_conf = 0.88 if 5 <= h_v <= 23 else 0.30
                rec[campo] = {"value": f"{h_v:02d}:{mn_v:02d}", "conf": sanity_conf}
            else:
                rec[campo] = {"value": None, "conf": 0.0}

        if any(rec[f]["value"] for f in campos):
            records.append(rec)

    return records
