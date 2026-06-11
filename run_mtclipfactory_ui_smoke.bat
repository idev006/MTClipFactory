@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Missing virtual environment at "%CD%\.venv".
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
set "PYTHONPATH=%CD%\src"
set "QT_QPA_PLATFORM=offscreen"

python scripts\ui_smoke_check.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] UI smoke completed successfully.
) else (
    echo [ERROR] UI smoke failed with code %EXIT_CODE%.
)

pause
exit /b %EXIT_CODE%
