#!/bin/bash
# Deployment script for VocoEng platform
# Deploys all services to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${1:-"vocoeng-dev"}
REGION=${2:-"us-central1"}

echo -e "${GREEN}Deploying VocoEng platform to GCP...${NC}"
echo -e "Project ID: ${YELLOW}$PROJECT_ID${NC}"
echo -e "Region: ${YELLOW}$REGION${NC}"

# Set project
gcloud config set project $PROJECT_ID

# Deploy webhook listener
echo -e "${GREEN}Deploying webhook listener service...${NC}"
cd vocoeng-webhook-listener
gcloud builds submit --config cloudbuild.yaml
cd ..

# Deploy processing worker
echo -e "${GREEN}Deploying processing worker service...${NC}"
cd vocoeng-worker
gcloud builds submit --config cloudbuild.yaml
cd ..

# Deploy Django frontend
echo -e "${GREEN}Deploying Django frontend service...${NC}"
cd vocoeng-django-frontend
gcloud builds submit --config cloudbuild.yaml
cd ..

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${YELLOW}Services deployed:${NC}"
echo -e "- Webhook Listener: https://vocoeng-webhook-listener-*.run.app"
echo -e "- Processing Worker: https://vocoeng-worker-*.run.app"
echo -e "- Django Frontend: https://vocoeng-django-frontend-*.run.app"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Configure custom domains"
echo -e "2. Set up SSL certificates"
echo -e "3. Configure monitoring and alerting"
echo -e "4. Test all endpoints"
