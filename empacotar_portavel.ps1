# ============================================================
#  Empacotador PORTÁTIL — Sistema de Cartão Ponto
#  Gera uma pasta autocontida (Python embutido + app + deps)
#  que o cliente descompacta e roda sem instalar nada.
#
#  Uso (uma vez, na SUA máquina):
#     powershell -ExecutionPolicy Bypass -File empacotar_portavel.ps1
#
#  No fim, zipe a pasta 'CONTROLE_DE_PONTO_PORTATIL' e envie ao cliente.
# ============================================================

$ErrorActionPreference = "Stop"
$ProjRoot = $PSScriptRoot
$PyVersion = "3.11.9"
$Dist = Join-Path $ProjRoot "CONTROLE_DE_PONTO_PORTATIL"
$Runtime = Join-Path $Dist "runtime"
$AppDir = Join-Path $Dist "app"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  EMPACOTANDO SISTEMA DE CARTAO PONTO (portatil)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Limpa pacote anterior
if (Test-Path $Dist) { Remove-Item $Dist -Recurse -Force }
New-Item -ItemType Directory -Path $Dist, $Runtime, $AppDir -Force | Out-Null

# 2. Baixa o Python embeddable
$embedZip = Join-Path $env:TEMP "python-embed.zip"
$embedUrl = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-amd64.zip"
Write-Host "`n[1/6] Baixando Python $PyVersion embutido..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $embedUrl -OutFile $embedZip -UseBasicParsing
Expand-Archive -Path $embedZip -DestinationPath $Runtime -Force
Remove-Item $embedZip

# 3. Habilita site-packages no ._pth (necessário para pip funcionar)
$pth = Get-ChildItem $Runtime -Filter "python*._pth" | Select-Object -First 1
$pthContent = @"
python311.zip
.
Lib\site-packages
import site
"@
Set-Content -Path $pth.FullName -Value $pthContent -Encoding ASCII
Write-Host "[2/6] Python embutido configurado." -ForegroundColor Green

# 4. Instala o pip no Python embutido
Write-Host "`n[3/6] Instalando pip..." -ForegroundColor Yellow
$getPip = Join-Path $env:TEMP "get-pip.py"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
& "$Runtime\python.exe" $getPip --no-warn-script-location
Remove-Item $getPip

# 5. Instala as dependências (versões fixas e compatíveis)
Write-Host "`n[4/6] Instalando dependencias (demora varios minutos)..." -ForegroundColor Yellow
& "$Runtime\python.exe" -m pip install --no-warn-script-location `
    "numpy==1.26.4" "opencv-python==4.6.0.66" `
    "fastapi==0.111.0" "uvicorn[standard]==0.29.0" "python-multipart==0.0.9" "aiofiles==23.2.1" `
    "Pillow==10.3.0" "pandas==2.2.2" "openpyxl==3.1.2" `
    "paddlepaddle==2.6.2" "paddleocr==2.7.3" "pytesseract==0.3.13"

# 6. Copia o app (sem lixo)
Write-Host "`n[5/6] Copiando arquivos do sistema..." -ForegroundColor Yellow
Copy-Item (Join-Path $ProjRoot "main.py")        $AppDir -Force
Copy-Item (Join-Path $ProjRoot "backend")        $AppDir -Recurse -Force
Copy-Item (Join-Path $ProjRoot "frontend")       $AppDir -Recurse -Force
Copy-Item (Join-Path $ProjRoot "CARTÃO PONTO.html") $AppDir -Force -ErrorAction SilentlyContinue
# pastas de dados vazias
New-Item -ItemType Directory -Path (Join-Path $AppDir "database"),(Join-Path $AppDir "uploads"),(Join-Path $AppDir "exports") -Force | Out-Null
# remove caches
Get-ChildItem $AppDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 7. Copia o lançador
Copy-Item (Join-Path $ProjRoot "INICIAR.vbs") $Dist -Force

# 8. Cria um LEIA-ME para o cliente
$leiame = @"
SISTEMA DE CARTAO PONTO
=======================

COMO USAR:
  1. Extraia esta pasta inteira em qualquer lugar (ex.: Area de Trabalho).
  2. De duplo-clique em INICIAR.vbs
  3. O navegador abre sozinho no sistema.

Para encerrar: feche o navegador e, no Gerenciador de Tarefas,
encerre o processo "python.exe" (ou apenas reinicie o PC).

Observacoes:
  - Tudo fica salvo automaticamente na pasta app\database.
  - A leitura de cartao por foto (OCR) precisa de internet na 1a vez
    (baixa os modelos). Depois funciona offline.
  - Tesseract (OCR alternativo) e opcional; o PaddleOCR ja vem incluido.
"@
Set-Content -Path (Join-Path $Dist "LEIA-ME.txt") -Value $leiame -Encoding UTF8

# 9. (Opcional) Pré-baixa os modelos do PaddleOCR para uso offline
Write-Host "`n[6/6] Pre-baixando modelos de OCR (opcional)..." -ForegroundColor Yellow
$env:HOME = $AppDir
try {
    & "$Runtime\python.exe" -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=False, lang='en', show_log=False)" 2>$null
    # move modelos baixados (~/.paddleocr) para dentro do app, se possivel
} catch { Write-Host "  (modelos serao baixados no 1o uso)" -ForegroundColor DarkGray }

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  PRONTO! Pasta gerada em:" -ForegroundColor Green
Write-Host "  $Dist" -ForegroundColor White
Write-Host "`n  Agora compacte essa pasta em .zip e envie ao cliente." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
