#!/bin/bash
# Start the API and the dashboard locally with demo data (Ctrl-C stops both).
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

python scripts/seed_data.py

echo "API on http://localhost:8000 (docs at /docs)"
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

echo "Dashboard on http://localhost:8501"
streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1
