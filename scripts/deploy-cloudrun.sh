#!/usr/bin/env bash
# Deploy the RemAgent dashboard (SPA + /api backend) to Google Cloud Run.
#
# One service serves everything: dist/server.cjs statically serves the built
# SPA and exposes the /api endpoints, so no separate static hosting is needed.
# The image is built remotely by Cloud Build from the repo Dockerfile — no
# local Docker daemon required.
#
# Prerequisites:
#   gcloud auth login
#   gcloud config set project <PROJECT_ID>
#   A Gemini API key (the service returns 503 on Gemini features without it).
#
# Usage:
#   GEMINI_API_KEY=... ./scripts/deploy-cloudrun.sh [service-name] [region]

set -euo pipefail

SERVICE="${1:-remagent-dashboard}"
REGION="${2:-us-central1}"

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "❌ FAILED: GEMINI_API_KEY is not set. Export it before deploying:" >&2
  echo "   GEMINI_API_KEY=... $0 $SERVICE $REGION" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2

echo
echo "Deployed. To map a custom domain (e.g. remagent.dev):"
echo "  gcloud beta run domain-mappings create --service $SERVICE --domain <your-domain> --region $REGION"
echo "then add the DNS records gcloud prints at your registrar."
