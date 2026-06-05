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

## Runtime Config

Runtime paths are stored in [app_config.toml](/F:/programming/python/MTClipFactory/app_config.toml).

- `ffprobe` points to `F:\ffmpeg\bin\ffprobe.exe`
- `ffmpeg` points to `F:\ffmpeg\bin\ffmpeg.exe`
