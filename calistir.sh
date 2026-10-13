#!/usr/bin/env bash
# Kullanım: ./calistir.sh baslangic.json komutlar.jsonl > sonuclar.jsonl
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || command -v python)"

SURUM="$("$PY" -c 'import sys; print(sys.version_info[:2])')"
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "Uyarı: Python 3.11+ önerilir (bulunan: $SURUM)" >&2
fi

PYTHONPATH="$DIR" PYTHONIOENCODING=utf-8 exec "$PY" -m rezervasyon "$@"
