# Obtenir la clé JSON GCP (GCP_SA_KEY)

Guide pour récupérer la clé du service account et l’ajouter dans GitHub.

---

## Option A : Console Google Cloud (interface web)

### 1. Créer le service account
1. Va sur [console.cloud.google.com](https://console.cloud.google.com)
2. Sélectionne le projet **clearborder-prod**
3. Menu **≡** → **IAM et administration** → **Comptes de service**
4. **+ Créer un compte de service**
5. Nom : `github-deploy` → **Créer et continuer**
6. Rôles : ajoute **Cloud Run Admin**, **Artifact Registry Writer**, **Service Account User**
7. **Terminer**

### 2. Télécharger la clé JSON
1. Clique sur le compte `github-deploy@clearborder-prod.iam.gserviceaccount.com`
2. Onglet **Clés** (Keys)
3. **Ajouter une clé** → **Créer une clé**
4. Type : **JSON** → **Créer**
5. Un fichier `.json` est téléchargé (ex : `clearborder-prod-xxxxx.json`)

### 3. Copier le contenu pour GitHub
```bash
# Ouvre le fichier dans VS Code (mode texte brut)
code ~/Downloads/clearborder-prod-*.json

# Ou affiche le contenu dans le terminal
cat ~/Downloads/clearborder-prod-*.json
```
- Sélectionne tout (Cmd+A), copie (Cmd+C)
- Le JSON doit commencer par `{` et finir par `}`

### 4. Ajouter le secret GitHub
1. [github.com/Pchambet/new-wave/settings/secrets/actions](https://github.com/Pchambet/new-wave/settings/secrets/actions)
2. **GCP_SA_KEY** → **Update** (ou **New repository secret**)
3. Name : `GCP_SA_KEY`
4. Secret : colle le contenu JSON (tout, du `{` au `}`)
5. **Update secret**

---

## Option B : Ligne de commande (gcloud)

### Prérequis
```bash
# Installer gcloud : https://cloud.google.com/sdk/docs/install
# Puis :
gcloud auth login
gcloud config set project clearborder-prod
```

### 1. Créer le service account
```bash
# Créer le SA
gcloud iam service-accounts create github-deploy --display-name="GitHub Deploy"

# Donner les rôles
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="github-deploy@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin" --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer" --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser" --quiet
```

### 2. Télécharger la clé JSON
```bash
# Créer la clé → fichier sa-key.json dans le dossier actuel
gcloud iam service-accounts keys create sa-key.json --iam-account=$SA_EMAIL

# Afficher le contenu (pour copier)
cat sa-key.json
```

### 3. Copier dans GitHub
1. Copie **tout** le contenu de `sa-key.json` (sortie de `cat sa-key.json`)
2. GitHub → Settings → Secrets → GCP_SA_KEY → Update
3. Colle le contenu
4. **⚠️ Supprime le fichier après** : `rm sa-key.json`

---

## Vérifier que le JSON est valide

```bash
# Si tu as le fichier localement
cat sa-key.json | python3 -m json.tool
# Si aucune erreur → JSON valide
```

Le JSON doit ressembler à :
```json
{
  "type": "service_account",
  "project_id": "clearborder-prod",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "github-deploy@clearborder-prod.iam.gserviceaccount.com",
  ...
}
```

**À éviter** : Word, Notes, PDF — utiliser uniquement un éditeur texte brut (VS Code, TextEdit en mode brut).
