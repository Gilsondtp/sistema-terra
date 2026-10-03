@echo off
chcp 65001 >nul 2>&1
title Sistema Terra - Python + SQLite
cd /d "%~dp0"

REM Verifica/instala pacotes caso ainda nao estejam instalados
python -c "import flask, watchdog, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias do Python pela primeira vez, aguarde...
    python -m pip install -r requirements.txt
)

REM Inicia o servidor em segundo plano usando pythonw (sem janela preta aberta)
start "" pythonw app.py

REM Aguarda 2 segundos e abre o navegador
timeout /t 2 /nobreak >nul
start http://localhost:5000
exit
