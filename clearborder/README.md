# ClearBorder

FastAPI service, Streamlit dashboard and pure-Python engine for CBAM specific embedded
emissions. See the [repository README](../README.md) for context, results and limitations.

## Run locally

```bash
cd clearborder
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python scripts/seed_data.py                      # demo installation, product, CN codes
uvicorn app.main:app --reload --port 8000        # API, docs at http://localhost:8000/docs
streamlit run dashboard/app.py --server.port 8501  # dashboard (second terminal)
```

`./run.sh` does the same in one command. With containers:

```bash
docker compose up                                # PostgreSQL + API + dashboard
docker compose run --rm api python scripts/seed_data.py   # once
docker compose -f docker-compose.sqlite.yml up   # lighter, SQLite only
```

## Checks

```bash
make lint       # ruff check + ruff format --check
make test       # pytest (about 10 s)
make test-cov   # with coverage
make example    # regenerate the README figure and docs/worked-example.json
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness (pings the database when it is not SQLite) |
| POST, GET | `/api/v1/installations` | Create / list non-EU installations |
| GET | `/api/v1/installations/{id}` | One installation |
| POST, GET | `/api/v1/products` | Create (with precursors) / list goods |
| GET | `/api/v1/products/{id}` | One good |
| POST | `/api/v1/generate-cbam-report` | SEE per good, 80/20 check, report XML |
| GET | `/api/v1/cn-codes` | Loaded CN codes |
| POST | `/api/v1/classify` | CN code suggestions for a description |

```bash
curl -X POST http://localhost:8000/api/v1/generate-cbam-report \
  -H "Content-Type: application/json" \
  -d '{"declarant_id": "EU-IMPORT-001", "reporting_period": "2026-Q1",
       "products": [{"product_id": 1, "quantity_tonnes": 10}]}'
```

With the demo data this returns `see_kg_co2_per_tonne: 1730.0`,
`real_data_ratio: 1.0`, `compliant_80_20: true` and the report XML.

## Configuration

Environment variables (or a `.env` file, see `.env.example`):

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./clearborder.db` | SQLAlchemy URL; PostgreSQL supported |
| `API_KEYS` | empty | Comma-separated keys for the `X-API-Key` header; empty disables auth |
| `DEBUG` | `false` | Echo SQL statements |
| `API_BASE` | `http://localhost:8000/api/v1` | Where the dashboard finds the API |
| `API_KEY` | empty | Key the dashboard sends as `X-API-Key` when the API requires one |

Tables are created at start-up (`create_all`); there are no migrations.
