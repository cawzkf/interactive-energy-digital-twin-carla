#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 --version
echo "--- checking deps ---"
python3 - <<'PY'
for mod in ("pydantic", "structlog", "dotenv", "pytest"):
    try:
        __import__(mod)
        print(f"ok: {mod}")
    except Exception as e:
        print(f"MISSING: {mod} ({e})")
PY
echo "--- running tests ---"
python3 -m pytest -q
