#!/bin/bash
# GCP Setup Script for VocoEng Platform
# This script sets up all required GCP resources for the VocoEng platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${1:-"vocoeng-dev"}
REGION=${2:-"us-central1"}
DB_INSTANCE_NAME="vocoeng-db"

echo -e "${GREEN}Setting up VocoEng platform on GCP...${NC}"
echo -e "Project ID: ${YELLOW}$PROJECT_ID${NC}"
echo -e "Region: ${YELLOW}$REGION${NC}"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${GREEN}Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    pubsub.googleapis.com \
    firestore.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    redis.googleapis.com

# Create Cloud SQL instance
echo -e "${GREEN}Creating Cloud SQL instance...${NC}"
gcloud sql instances create $DB_INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup \
    --enable-bin-log

# Create database
echo -e "${GREEN}Creating database...${NC}"
gcloud sql databases create vocoeng_db --instance=$DB_INSTANCE_NAME

# Create Pub/Sub topics
echo -e "${GREEN}Creating Pub/Sub topics...${NC}"
gcloud pubsub topics create vocoeng-messages
gcloud pubsub topics create vocoeng-responses

# Create Pub/Sub subscriptions
echo -e "${GREEN}Creating Pub/Sub subscriptions...${NC}"
gcloud pubsub subscriptions create vocoeng-messages-sub \
    --topic=vocoeng-messages \
    --ack-deadline=600
gcloud pubsub subscriptions create vocoeng-django-sub \
    --topic=vocoeng-responses \
    --ack-deadline=60

# Create service accounts
echo -e "${GREEN}Creating service accounts...${NC}"

# Webhook listener service account
gcloud iam service-accounts create vocoeng-webhook-listener \
    --display-name="VocoEng Webhook Listener"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-webhook-listener@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-webhook-listener@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Worker service account
gcloud iam service-accounts create vocoeng-worker \
    --display-name="VocoEng Processing Worker"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-worker@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-worker@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-worker@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-worker@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Django frontend service account
gcloud iam service-accounts create vocoeng-django-frontend \
    --display-name="VocoEng Django Frontend"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-django-frontend@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-django-frontend@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vocoeng-django-frontend@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Create secrets
echo -e "${GREEN}Creating secrets...${NC}"
echo -n "your-secure-api-key" | gcloud secrets create api-webhook-key --data-file=-
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "your-django-secret-key" | gcloud secrets create django-secret-key --data-file=-
echo -n "your-database-password" | gcloud secrets create database-password --data-file=-
echo -n "your-email-password" | gcloud secrets create email-password --data-file=-

# Create Cloud Build triggers (requires manual setup)
echo -e "${YELLOW}Cloud Build triggers need to be set up manually:${NC}"
echo -e "1. Go to Cloud Build > Triggers"
echo -e "2. Create trigger for vocoeng-webhook-listener"
echo -e "3. Create trigger for vocoeng-worker"
echo -e "4. Create trigger for vocoeng-django-frontend"
echo -e "5. Connect to your GitHub repository"

# Create Firestore database
echo -e "${GREEN}Creating Firestore database...${NC}"
gcloud firestore databases create --region=$REGION

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Update secrets with real values"
echo -e "2. Set up Cloud Build triggers"
echo -e "3. Deploy services using: gcloud builds submit --config cloudbuild.yaml"
echo -e "4. Configure domain and SSL certificates"
