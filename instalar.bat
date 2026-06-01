@echo off
echo ============================================
echo  INSTALANDO DEPENDENCIAS - CARTAO PONTO
echo ============================================
echo.

pip install fastapi "uvicorn[standard]" python-multipart opencv-python numpy Pillow pandas openpyxl aiofiles
echo.
echo Instalando PaddleOCR (pode demorar alguns minutos)...
pip install paddlepaddle paddleocr
echo.
echo Instalando pytesseract (fallback)...
pip install pytesseract
echo.
echo ============================================
echo  INSTALACAO CONCLUIDA!
echo  Execute iniciar.bat para abrir o sistema.
echo ============================================
pause
