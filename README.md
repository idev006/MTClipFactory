# MTClipFactory

`MTClipFactory` is a workflow-driven desktop application for assembling product video advertisements from reusable media ingredients.

The project is intentionally document-led. Start with the files in [doc/00_Document_Index.md](/F:/programming/python/MTClipFactory/doc/00_Document_Index.md).

## Development Notes

Use the project virtual environment at `F:\programming\python\MTClipFactory\.venv` only.

Typical local setup:

```powershell
& F:\programming\python\MTClipFactory\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m pytest
mt-resource-library
```

`mt-resource-library` now opens the dashboard/control-center window first, then lets the user open Products, Assets, Tags, and Settings from there.

## Quick Test Launchers

Use these batch files from the repo root when you want a repeatable local test flow without typing commands manually:

- `run_mtclipfactory_ui.bat`
- `run_mtclipfactory_pytest.bat`
- `run_mtclipfactory_ui_smoke.bat`

`run_mtclipfactory_ui.bat` opens the desktop UI and should show the dashboard first.

`run_mtclipfactory_pytest.bat` runs the pytest regression suite inside `F:\programming\python\MTClipFactory\.venv`.

`run_mtclipfactory_ui_smoke.bat` runs a non-interactive offscreen smoke check that builds all six main windows and prints `ui_smoke_ok=6` on success.

`python scripts/full_system_release_audit.py` runs the scripted release-audit workflow for factory, recovery, and runtime hot-reload evidence capture.

## Runtime Config

Runtime paths are stored in [app_config.toml](/F:/programming/python/MTClipFactory/app_config.toml).

- `ffprobe` points to `F:\ffmpeg\bin\ffprobe.exe`
- `ffmpeg` points to `F:\ffmpeg\bin\ffmpeg.exe`
