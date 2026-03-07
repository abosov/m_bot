# Deploy Checks

## Encoding Guard

`python scripts/check_encoding.py` validates only repository text files and skips runtime/media assets.

- Checked extensions: `.py`, `.sql`, `.md`, `.yaml`, `.yml`, `.json`, `.env`, `.txt`
- Ignored directories: `specialist`, `media`, `static`, `.git`, `.venv`, `__pycache__`
- Binary/media assets (for example, `specialist/<uuid>/photo/*.jpg`) are excluded from UTF-8 validation.

Purpose: prevent accidental non-UTF-8 text commits while avoiding false failures on uploaded/runtime binary files.
