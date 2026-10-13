#!/usr/bin/env bash
# Kullanım: ./arayuz.sh [baslangic.json]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$DIR/.venv/bin/python" ]; then
    PY="$DIR/.venv/bin/python"
else
    PY="$(command -v python3 || command -v python)"
fi
if ! "$PY" -c 'import PySide6' 2>/dev/null; then
    echo "PySide6 bulunamadı ($PY). Kurulum: $PY -m pip install -r \"$DIR/requirements.txt\"" >&2
    exit 1
fi
PYTHONPATH="$DIR" PYTHONIOENCODING=utf-8 exec "$PY" -m arayuz "$@"
