@echo off
chcp 65001 >nul 2>&1
echo Encerrando o servidor do Sistema Terra em segundo plano...
taskkill /F /IM pythonw.exe >nul 2>&1
echo Sistema encerrado com sucesso!
timeout /t 2 >nul
