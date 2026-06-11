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

python -m mt_clip_factory.ui.main
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] MTClipFactory UI exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
