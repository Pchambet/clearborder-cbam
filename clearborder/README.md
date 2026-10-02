# ClearBorder — Moteur CBAM & Landed Cost

**Calcul automatique des émissions intégrées (SEE) pour la conformité CBAM EU.**

## Démarrage rapide

### Option A : Python local (recommandé pour le dev)

```bash
cd clearborder
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt

# Charger les données de démo
python scripts/seed_data.py

# Lancer l'API
uvicorn app.main:app --reload --port 8000

# Dans un autre terminal : Lancer le dashboard
streamlit run dashboard/app.py --port 8501
```

### Option B : Conteneurs avec PostgreSQL (prod-like)

Sur Mac, [OrbStack](https://orbstack.dev) est recommandé.

```bash
cd clearborder
docker compose up
make seed   # au 1er lancement : données de démo
```

Mode SQLite (plus léger, sans PostgreSQL) :
```bash
docker compose -f docker-compose.sqlite.yml up
```

- **API** : http://localhost:8000
- **Documentation** : http://localhost:8000/docs
- **Dashboard** : http://localhost:8501

## Structure

```
clearborder/
├── app/
│   ├── main.py          # FastAPI app
│   ├── routes.py        # Endpoints
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── services.py      # Business logic
│   ├── cbam_engine.py   # Calcul SEE (Annexe IV Règlement 2023/956)
│   ├── xml_generator.py # Export XML CBAM
│   ├── database.py
│   └── config.py
├── dashboard/
│   └── app.py           # Streamlit UI
├── scripts/
│   └── seed_data.py    # Données de démo
└── requirements.txt
```

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/installations` | Créer une installation |
| GET | `/api/v1/installations` | Lister les installations |
| POST | `/api/v1/products` | Créer un produit (avec précurseurs) |
| GET | `/api/v1/products` | Lister les produits |
| POST | `/api/v1/generate-cbam-report` | Générer le rapport XML CBAM |

## Exemple : Générer un rapport CBAM

```bash
curl -X POST http://localhost:8000/api/v1/generate-cbam-report \
  -H "Content-Type: application/json" \
  -d '{
    "declarant_id": "EU-IMPORT-001",
    "reporting_period": "2026-Q1",
    "products": [
      {"product_id": 1, "quantity_tonnes": 10}
    ]
  }'
```

## Formule CBAM (Annexe IV)

```
SEE_g = (AttrEm_g + EEInpMat) / AL_g
EEInpMat = Σ (M_i × SEE_i)
```

- **SEE** : Specific Embedded Emissions (kg CO2e/kg)
- **AttrEm** : Émissions du processus de production
- **EEInpMat** : Émissions des précurseurs
- **AL** : Niveau d'activité (masse du produit)
- **Règle 80/20** : ≥80% des données doivent être réelles pour les biens complexes

## Licence

Propriétaire — ClearBorder / New Wave
