"""
Pré-processamento de imagem com OpenCV.
Prepara a imagem do cartão ponto para OCR.
"""

import cv2
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def load_image(path: str) -> np.ndarray:
    """Carrega imagem de arquivo (suporta PDF via primeira página)."""
    path = str(path)
    if path.lower().endswith(".pdf"):
        return _load_pdf_page(path)
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Não foi possível carregar: {path}")
    return img


def _load_pdf_page(path: str) -> np.ndarray:
    """Converte primeira página do PDF em imagem."""
    try:
        from PIL import Image
        import io
        # Tenta pypdf2 para extrair imagem embutida
        try:
            import fitz  # pymupdf
            doc = fitz.open(path)
            page = doc[0]
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom = ~144 DPI
            clip = page.get_pixmap(matrix=mat)
            img_bytes = clip.tobytes("png")
            arr = np.frombuffer(img_bytes, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except ImportError:
            pass
        # Fallback: converte com Pillow se disponível
        from PIL import Image as PILImage
        img = PILImage.open(path).convert("RGB")
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise ValueError(f"Erro ao processar PDF: {e}")


def preprocess(img: np.ndarray) -> np.ndarray:
    """
    Pipeline completo de pré-processamento:
    1. Converte para escala de cinza
    2. Remove ruído
    3. Corrige inclinação (deskew)
    4. Melhora contraste (CLAHE)
    5. Binariza com threshold adaptativo
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    # Redimensiona se muito pequena
    h, w = gray.shape
    if max(h, w) < 1000:
        scale = 1000 / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Remove ruído
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # Deskew
    deskewed = _deskew(denoised)

    # CLAHE para melhorar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(deskewed)

    # Threshold adaptativo
    binary = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15, C=10
    )

    return binary


def _deskew(img: np.ndarray) -> np.ndarray:
    """Detecta e corrige ângulo de inclinação da imagem."""
    try:
        coords = np.column_stack(np.where(img < 128))
        if len(coords) < 100:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        # Só corrige se inclinação for significativa
        if abs(angle) < 0.5 or abs(angle) > 30:
            return img
        h, w = img.shape
        cx, cy = w // 2, h // 2
        M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return img


def detect_table_region(img: np.ndarray) -> tuple[int, int, int, int] | None:
    """
    Tenta detectar a região da tabela de horários na imagem.
    Retorna (x, y, w, h) ou None.
    """
    # Binariza para detecção de linhas
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Detecta linhas horizontais
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    h_lines  = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)

    # Detecta linhas verticais
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    v_lines  = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)

    # Une linhas
    grid = cv2.add(h_lines, v_lines)

    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # Maior contorno = região da tabela
    largest = max(contours, key=cv2.contourArea)
    x, y, w, h_r = cv2.boundingRect(largest)
    area = w * h_r
    img_area = img.shape[0] * img.shape[1]

    # Ignora regiões muito pequenas (< 10% da imagem)
    if area < img_area * 0.10:
        return None

    return (x, y, w, h_r)


def extract_row_cells(img: np.ndarray, table_region=None) -> list[dict]:
    """
    Detecta linhas da tabela e recorta células por linha.
    Retorna lista de dicts com roi (imagem recortada) por linha.
    """
    region = img
    if table_region:
        x, y, w, h = table_region
        region = img[y:y+h, x:x+w]

    if len(region.shape) == 3:
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    else:
        gray = region.copy()

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Linhas horizontais
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(gray.shape[1] * 0.5), 1))
    h_lines  = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)

    # Projeção horizontal para encontrar Y das linhas
    proj = np.sum(h_lines, axis=1)
    threshold = proj.max() * 0.3
    line_ys = np.where(proj > threshold)[0]

    if len(line_ys) < 2:
        return []

    # Agrupa linhas próximas
    groups = []
    group = [line_ys[0]]
    for y_val in line_ys[1:]:
        if y_val - group[-1] <= 5:
            group.append(y_val)
        else:
            groups.append(int(np.mean(group)))
            group = [y_val]
    groups.append(int(np.mean(group)))

    # Recorta entre linhas horizontais
    rows = []
    for i in range(len(groups) - 1):
        y1, y2 = groups[i], groups[i + 1]
        row_h = y2 - y1
        if row_h < 8:
            continue
        roi = region[y1:y2, :]
        rows.append({"y1": y1, "y2": y2, "roi": roi})

    return rows
