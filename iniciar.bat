@echo off
title Vigilante Master v14.0 - LOCAL CORE
echo ====================================================================
echo    HERMES AGENT: INICIALIZADOR LOCAL AUTOMATICO
echo ====================================================================
echo.

:: Caminho atualizado para a sua pasta do OneDrive Desktop
set PASTA_PROJETO=C:\Users\Leand\OneDrive\Desktop\vigilante

echo [*] AGUARDANDO CRITICO: Dando 30 segundos para o Windows estabilizar a rede e os servicos...
timeout /t 30

echo [*] Navegando ate a pasta do projeto...
cd /d "%PASTA_PROJETO%"

echo ====================================================================
echo 🔥 DISPARANDO MOTOR PRINCIPAL NATIVO (MAIN.PY)
echo ====================================================================
echo.

:: Executa o main.py usando o executável interno da nova venv estável
"%PASTA_PROJETO%\venv\Scripts\python.exe" -u main.py

echo.
echo [!] Script finalizado ou interrompido.
pause