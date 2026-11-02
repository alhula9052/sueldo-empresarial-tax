@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 (
        py -3.12 scripts\launch_local.py
        goto :finished
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python scripts\launch_local.py
    goto :finished
)
echo Instale Python 3.12 desde https://www.python.org/downloads/windows/
echo Marque "Add python.exe to PATH" durante la instalacion y vuelva a abrir este archivo.
pause
exit /b 1
:finished
if errorlevel 1 pause
endlocal
