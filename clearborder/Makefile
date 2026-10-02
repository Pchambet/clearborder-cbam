# ClearBorder — Makefile
# Sur Mac : OrbStack recommandé (orbstack.dev)
.PHONY: test test-cov install run-api run-dashboard up seed

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

install:
	pip install -r requirements.txt

run-api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard:
	streamlit run dashboard/app.py --server.headless true

# Conteneurs (PostgreSQL)
up:
	docker compose up

# Données de démo (à lancer après le 1er docker compose up)
seed:
	docker compose run --rm api python scripts/seed_data.py
