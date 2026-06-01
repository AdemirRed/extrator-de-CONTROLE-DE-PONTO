"""
Rota OCR — suporta face única ou as duas faces do cartão DATAPRINT.

POST /api/ocr/processar
  - file       : imagem/PDF da face 1 (dias 1-15)
  - file2      : imagem/PDF da face 2 (dias 16-31) — opcional
  - funcionario_id: id do funcionário
  - conf_minima: confiança mínima (default 0.50)
"""

import shutil
import uuid
import traceback
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional

from backend.ocr.processor import load_image, preprocess
from backend.ocr.extractor import extract_card_structured

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".pdf", ".webp"}


def _save_upload(file: UploadFile) -> Path:
    ext  = Path(file.filename or "img.jpg").suffix.lower() or ".jpg"
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Formato não suportado: {ext}")
    path = UPLOADS_DIR / f"{uuid.uuid4().hex}{ext}"
    with path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return path


def _process_face(path: Path, face: int, conf_min: float) -> list[dict]:
    img_orig  = load_image(str(path))
    processed = preprocess(img_orig)
    # Passa a imagem original (não binarizada) para melhor detecção de grade
    # O extractor faz seu próprio pré-processamento interno
    extracted = extract_card_structured(img_orig, face=face)

    # Marca campos abaixo da confiança mínima
    valid = []
    for row in extracted:
        has = False
        for campo in ["entrada","inicio_intervalo","fim_intervalo","saida"]:
            f = row.get(campo, {})
            if f.get("value"):
                has = True
                if (f.get("conf") or 0) < conf_min:
                    f["value"]    = None
                    f["low_conf"] = True
                else:
                    f["low_conf"] = False
        if has:
            valid.append(row)
    return valid


@router.post("/processar")
async def processar_cartao(
    file:           UploadFile        = File(...),
    file2:          Optional[UploadFile] = File(None),
    funcionario_id: Optional[int]     = Form(None),
    conf_minima:    Optional[float]   = Form(0.50),
):
    """
    Processa uma ou duas faces do cartão ponto.
    Face 1 (file) = dias 1-15.
    Face 2 (file2) = dias 16-31 (opcional).
    """
    try:
        path1  = _save_upload(file)
        valid1 = _process_face(path1, face=1, conf_min=conf_minima)

        valid2   = []
        arquivo2 = None
        if file2 and file2.filename:
            path2    = _save_upload(file2)
            valid2   = _process_face(path2, face=2, conf_min=conf_minima)
            arquivo2 = path2.name

        all_valid = valid1 + valid2

        return {
            "ok":                True,
            "arquivo":           path1.name,
            "arquivo2":          arquivo2,
            "engine_used":       "PaddleOCR",
            "linhas_detectadas": len(all_valid),
            "linhas_validas":    len(all_valid),
            "duas_faces":        bool(file2 and file2.filename),
            "face1_count":       len(valid1),
            "face2_count":       len(valid2),
            "funcionario_id":    funcionario_id,
            "registros":         all_valid,
            "msg": (
                f"Face 1: {len(valid1)} dia(s) · Face 2: {len(valid2)} dia(s)"
                if (file2 and file2.filename)
                else f"{len(valid1)} dia(s) detectado(s)"
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erro OCR: {str(e)}\n{traceback.format_exc()}")


@router.get("/status")
def status_ocr():
    engines: dict = {}

    # PaddleOCR — opcional, so mostra se instalado
    try:
        from paddleocr import PaddleOCR
        engines["PaddleOCR"] = True
    except Exception:
        pass  # nao mostra no UI se nao instalado

    # Tesseract — principal
    try:
        import pytesseract
        for _tp in [
            r"C:\Users\SCM\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        ]:
            if Path(_tp).exists():
                pytesseract.pytesseract.tesseract_cmd = _tp
                break
        ver = pytesseract.get_tesseract_version()
        engines["Tesseract"] = str(ver)
    except Exception:
        engines["Tesseract"] = False

    # OpenCV — suporte
    try:
        import cv2
        engines["OpenCV"] = cv2.__version__
    except Exception:
        engines["OpenCV"] = False

    tess_ok = bool(engines.get("Tesseract") and engines["Tesseract"] is not False)
    paddle_ok = bool(engines.get("PaddleOCR"))
    return {
        "engines": engines,
        "ready": tess_ok or paddle_ok,
        "engine_name": "PaddleOCR" if paddle_ok else ("Tesseract" if tess_ok else None),
    }
