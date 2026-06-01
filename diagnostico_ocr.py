"""
Script de diagnostico OCR - processa uma imagem do cartao e mostra
o que o Tesseract le para entender o padrao do cartao DATAPRINT.

Uso: python diagnostico_ocr.py [face]
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# Configura Tesseract
_TESS_PATHS = [
    r"C:\Users\SCM\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
]
import pytesseract
for _p in _TESS_PATHS:
    if Path(_p).exists():
        pytesseract.pytesseract.tesseract_cmd = _p
        break


def prepare(img, scale=3):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    h, w = gray.shape
    big = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enh = clahe.apply(big)
    den = cv2.fastNlMeansDenoising(enh, h=7)
    return den


SEP = "-" * 60

face = int(sys.argv[1]) if len(sys.argv) > 1 else 1

# Lista uploads
uploads = list(Path("uploads").glob("*"))
if not uploads:
    print("Nenhuma imagem em uploads/")
    sys.exit(1)

img_path = str(sorted(uploads, key=lambda p: p.stat().st_mtime)[-1])
print(f"Usando: {img_path} (face {face})")

img = cv2.imread(img_path)
if img is None:
    print(f"ERRO: nao carregou {img_path}")
    sys.exit(1)

print(f"Tamanho: {img.shape[1]}x{img.shape[0]} px")

img_prep = prepare(img, scale=3)
print(f"Processado: {img_prep.shape[1]}x{img_prep.shape[0]} px")

# Texto completo PSM 6, 11
for psm in [6, 11]:
    print(f"\n{SEP}")
    print(f"PSM {psm} - texto:")
    txt = pytesseract.image_to_string(img_prep, lang="eng",
                                      config=f"--psm {psm} --oem 3")
    for line in txt.splitlines():
        if line.strip():
            print(f"  {repr(line)}")

# image_to_data PSM 6
print(f"\n{SEP}")
print("image_to_data PSM6 - palavras com posicao Y,X:")
data = pytesseract.image_to_data(img_prep, lang="eng",
                                  config="--psm 6 --oem 3",
                                  output_type=pytesseract.Output.DICT)
words = []
for i, txt in enumerate(data["text"]):
    txt = txt.strip()
    if not txt:
        continue
    conf = int(data["conf"][i])
    if conf < 0:
        continue
    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
    words.append((y, x, txt, conf))

words.sort()
prev_y = -999
for y, x, txt, conf in words[:100]:
    if abs(y - prev_y) > 15:
        print()
    print(f"  Y={y:4d} X={x:4d}  {txt!r:14s} conf={conf}%")
    prev_y = y

# Extrator
print(f"\n{SEP}")
print(f"Extrator (face {face}):")
from backend.ocr.extractor import extract_card_structured
result = extract_card_structured(img, face=face)
if not result:
    print("  NENHUM DIA DETECTADO!")
for r in result:
    campos = ["entrada", "inicio_intervalo", "fim_intervalo", "saida"]
    vals = " | ".join(f"{c}: {r.get(c, {}).get('value', '--')}" for c in campos)
    print(f"  Dia {r['dia']:2d}: {vals}")

print(f"\n{SEP}")
print(f"Total: {len(result)} dias detectados")
