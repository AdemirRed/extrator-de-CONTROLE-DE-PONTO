@echo off
title Empacotar Sistema de Cartao Ponto
echo ============================================================
echo   GERANDO PACOTE PORTATIL PARA O CLIENTE
echo   (baixa Python embutido + instala tudo + compacta)
echo ============================================================
echo.
cd /d "%~dp0"

REM Roda o script de empacotamento sem precisar mudar politica do sistema
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0empacotar_portavel.ps1"

echo.
echo ============================================================
echo   Agora compactando a pasta em .zip ...
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (Test-Path 'CONTROLE_DE_PONTO_PORTATIL.zip') { Remove-Item 'CONTROLE_DE_PONTO_PORTATIL.zip' -Force }; Compress-Archive -Path 'CONTROLE_DE_PONTO_PORTATIL\*' -DestinationPath 'CONTROLE_DE_PONTO_PORTATIL.zip' -CompressionLevel Optimal; Write-Host ('ZIP gerado: ' + [math]::Round((Get-Item 'CONTROLE_DE_PONTO_PORTATIL.zip').Length/1MB,1) + ' MB')"

echo.
echo ============================================================
echo   PRONTO! Envie o arquivo CONTROLE_DE_PONTO_PORTATIL.zip
echo ============================================================
pause
