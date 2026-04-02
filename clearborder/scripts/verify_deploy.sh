#!/bin/bash
# Vérification du déploiement Cloud Run
# Usage: ./scripts/verify_deploy.sh https://clearborder-api-xxxxx.run.app

set -e
URL="${1:-}"
if [ -z "$URL" ]; then
  echo "Usage: $0 <URL_API_CLOUD_RUN>"
  echo "Exemple: $0 https://clearborder-api-xxxxx-ew.a.run.app"
  exit 1
fi

echo "=== Vérification de $URL ==="
echo ""

echo "1. Health check..."
curl -sf "$URL/health" | jq . 2>/dev/null || curl -sf "$URL/health"
echo ""
echo "   ✓ Health OK"
echo ""

echo "2. Root..."
curl -sf "$URL/" | jq . 2>/dev/null || curl -sf "$URL/"
echo ""
echo "   ✓ Root OK"
echo ""

echo "3. Docs API..."
if curl -sf -o /dev/null -w "%{http_code}" "$URL/docs" | grep -q 200; then
  echo "   ✓ Docs accessibles: $URL/docs"
else
  echo "   ⚠ Vérifier: $URL/docs"
fi
echo ""

echo "4. Installations (doit retourner [] si vide)..."
curl -sf "$URL/api/v1/installations" | jq . 2>/dev/null || curl -sf "$URL/api/v1/installations"
echo ""
echo "   ✓ API installations OK"
echo ""

echo "=== Tous les checks passés ==="
echo ""
echo "Prochaine étape: lancer 'make seed' (ou python scripts/seed_data.py avec DATABASE_URL)"
echo "pour ajouter les données de démo."
