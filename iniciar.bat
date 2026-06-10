@echo off
title Vigilante Master v14.0 - LOCAL CORE
echo ====================================================================
echo    HERMES AGENT: INICIALIZADOR LOCAL AUTOMATICO
echo ====================================================================
echo.

:: Caminho atualizado para a sua pasta do OneDrive Desktop
set PASTA_PROJETO=C:\Users\Leand\OneDrive\Desktop\vigilante

echo [*] LIMPANDO PROCESSOS OCULTOS ANTIGOS...
taskkill /f /im chrome.exe >nul 2>&1
taskkill /f /im chromedriver.exe >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE ne %CmdCmdLine%" >nul 2>&1

echo [*] LIMPANDO ARQUIVOS TEMPORARIOS DO CHROME (LIBERANDO ESPACO)...
powershell -Command "Remove-Item -Path $env:TEMP\tmp* -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -Path $env:TEMP\scoped_dir* -Recurse -Force -ErrorAction SilentlyContinue"

echo [*] AGUARDANDO ESTABILIZACAO DA REDE (10 segundos)...
timeout /t 10

echo [*] Navegando ate a pasta do projeto...
cd /d "%PASTA_PROJETO%"

echo ====================================================================
echo 🔥 DISPARANDO MOTOR PRINCIPAL NATIVO (MAIN.PY)
echo ====================================================================
echo.

:loop
:: Executa o main.py usando o executável interno da nova venv estável
"%PASTA_PROJETO%\venv\Scripts\python.exe" -u main.py > terminal.log 2>&1

echo.
echo [!] Script finalizado ou interrompido. Reiniciando em 10 segundos...
timeout /t 10
goto loop