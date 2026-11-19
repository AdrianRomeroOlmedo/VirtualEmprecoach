@echo off
cd /d "%~dp0"
title Virtual EmpreCoach
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
if errorlevel 1 (
    echo.
    echo No se pudo iniciar Virtual EmpreCoach. Consulta el mensaje anterior.
    pause
)
