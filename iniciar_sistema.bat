@echo off
setlocal
chcp 65001 >nul 2>&1
title Sistema Terra - Python + SQLite
cd /d "%~dp0"

REM Resolve o Python 3 instalado; o Launcher pode funcionar mesmo sem python.exe no PATH.
set "PYTHON_EXE="
where py >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%I"
)
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%I"
    )
)
if not defined PYTHON_EXE goto :python_missing

REM pythonw.exe normalmente fica ao lado do python.exe; usa o caminho completo.
for %%I in ("%PYTHON_EXE%") do set "PYTHON_DIR=%%~dpI"
set "PYTHONW_EXE=%PYTHON_DIR%pythonw.exe"
set "PYTHONW_ARGS="
if not exist "%PYTHONW_EXE%" (
    where pyw >nul 2>&1
    if errorlevel 1 goto :pythonw_missing
    set "PYTHONW_EXE=pyw"
    set "PYTHONW_ARGS=-3"
)

REM Instala as dependências apenas se ainda não estiverem disponíveis.
"%PYTHON_EXE%" -c "import flask, watchdog, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias Python pela primeira vez, aguarde...
    "%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo.
        echo Nao foi possivel instalar as dependencias. Verifique a conexao com a internet e tente novamente.
        pause
        exit /b 1
    )
)

REM Inicia em segundo plano usando o caminho descoberto acima.
start "" "%PYTHONW_EXE%" %PYTHONW_ARGS% "%~dp0app.py"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5000
exit /b 0

:python_missing
echo Python 3 nao foi encontrado nesta maquina virtual.
echo Instale Python 3 para Windows e marque as opcoes Python Launcher e Add Python to PATH.
echo Depois execute este arquivo novamente.
pause
exit /b 1

:pythonw_missing
echo Python foi encontrado em:
echo %PYTHON_EXE%
echo mas nao foi localizado pythonw.exe nem o Launcher pyw.
echo Reinstale ou modifique a instalacao oficial do Python para incluir esses componentes.
pause
exit /b 1
