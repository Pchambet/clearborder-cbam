# Déploiement 100 % gratuit — ClearBorder

Stack 100 % free tier : **Neon** (PostgreSQL) + **Cloud Run** + **GitHub Actions**.

> ⚠️ GCP exige une carte pour activer Cloud Run, mais le free tier = **0€** si on reste dans les limites. Configurer une alerte budget à 1€ pour être notifié.

---

## Limites free tier (par mois)

| Service | Gratuit | Au-delà |
|---------|---------|---------|
| **Neon** | 0.5 GB stockage, 1 projet | Payant |
| **Cloud Run** | 2M requêtes, 360K GB-s mémoire | ~0,00002€/req |
| **Cloud Build** | 120 min/jour | Payant |
| **Artifact Registry** | 0,5 GB | ~0,10€/GB |
| **GitHub Actions** | 2000 min/mois (repo privé) ou illimité (public) | Payant |

Pour un MVP avec trafic faible : **0€**.

---

## Setup en 20 min (une seule fois)

### 1. Neon — PostgreSQL gratuit (5 min)

1. Aller sur [neon.tech](https://neon.tech) → Sign up (GitHub)
2. **New Project** → Nom : `clearborder`
3. Région : `EU Central (Frankfurt)` pour latence Europe
4. Copier la **connection string** (Format: Connection string)
   - Exemple : `postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`

### 2. Google Cloud (5 min)

1. [console.cloud.google.com](https://console.cloud.google.com) → Nouveau projet `clearborder-prod`
2. **Facturation** : lier un compte (carte requise pour Cloud Run)
3. **Budget & alertes** : créer un budget à 1€ avec email d’alerte à 50% et 90%

```bash
# Ou en CLI :
gcloud config set project clearborder-prod
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### 3. Service account pour GitHub (5 min)

```bash
# Créer le SA
gcloud iam service-accounts create github-deploy --display-name="GitHub Deploy"

# Rôles (minimal pour deploy)
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="github-deploy@${PROJECT_ID}.iam.gserviceaccount.com"

for role in run.admin artifactregistry.writer iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/${role}" --quiet
done

# Télécharger la clé JSON
gcloud iam service-accounts keys create sa-key.json --iam-account=$SA_EMAIL
# ⚠️ Ne jamais commit sa-key.json ! L'ajouter à .gitignore
```

### 4. Secrets GitHub (2 min)

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** :

| Nom | Valeur |
|-----|--------|
| `GCP_PROJECT_ID` | `clearborder-prod` (ou ton project ID) |
| `GCP_SA_KEY` | Contenu du fichier `sa-key.json` |
| `DATABASE_URL` | La connection string Neon (avec `?sslmode=require`) |

### 5. Seed des données (une fois déployé)

Après le premier push sur `main` et déploiement réussi :

```bash
# Option A : En local, pointer vers la DB Neon et l’API déployée
export DATABASE_URL="postgresql://..."  # ta connection Neon
cd clearborder && python scripts/seed_data.py

# Option B : Cloud Run Job (si tu veux tout dans le cloud)
# Créer un job qui exécute seed_data.py - voir DEPLOIEMENT.md
```

Comme l’API et le seed utilisent la même `DATABASE_URL` Neon, le seed en local suffit : les données seront visibles par l’API déployée.

---

## Vérifier le déploiement

1. Push sur `main` → le workflow GitHub Actions déploie
2. Dans l’onglet **Actions**, récupérer l’URL du service
3. Lancer `./scripts/verify_deploy.sh https://TON-URL` ou tester :
   `curl https://ton-url/health`

---

## Rester à 0€

1. **Budget GCP** : alerte à 1€
2. **Neon** : rester sous 0,5 GB et 1 projet
3. **Trafic** : < 2M requêtes/mois sur Cloud Run
4. **Images** : ne garder que la dernière image (éviter l’accumulation dans Artifact Registry)

---

## Alternative sans GCP (si pas de carte)

- **[Render](https://render.com)** : free tier (avec carte), spin-down après inactivité
- **[Fly.io](https://fly.io)** : 3 machines gratuites
- **[Railway](https://railway.app)** : ~5€ de crédit gratuit/mois

On peut ajouter un `render.yaml` si tu veux cette option.

---

*ClearBorder — New Wave — Déploiement gratuit*
