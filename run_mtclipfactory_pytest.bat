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

python -m pytest
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] Pytest completed successfully.
) else (
    echo [ERROR] Pytest failed with code %EXIT_CODE%.
)

pause
exit /b %EXIT_CODE%
