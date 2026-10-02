#!/bin/bash
# Start the API and the dashboard locally with demo data (Ctrl-C stops both).
# Needs Python 3.11 to 3.14; set PYTHON=/path/to/python to choose the interpreter.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    PY=${PYTHON:-python3}
    if ! "$PY" -c 'import sys; sys.exit(not (3, 11) <= sys.version_info[:2] <= (3, 14))'; then
        echo "ClearBorder needs Python 3.11 to 3.14; $PY is $("$PY" --version 2>&1)." >&2
        echo "Run again with PYTHON=python3.12 (or another supported interpreter)." >&2
        exit 1
    fi
    "$PY" -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

python scripts/seed_data.py

echo "API on http://localhost:8000 (docs at /docs)"
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

echo "Dashboard on http://localhost:8501"
streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
