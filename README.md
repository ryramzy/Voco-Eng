# VocoEng AI Coder Platform

A serverless conversational AI platform built on Google Cloud Platform (GCP) with three microservices architecture.

## Architecture Overview

VocoEng follows a serverless, event-driven, and stateless architecture pattern:

- **Service 1: Webhook Listener** - Flask app on Cloud Run, receives external webhooks (WhatsApp, APIs)
- **Service 2: Processing Worker** - Python app on Cloud Run, executes AI processing & API calls (OpenAI, others)
- **Service 3: Django Frontend/Analytics** - Django REST Framework + Admin dashboard on Cloud Run with Cloud SQL

## Technology Stack

- **Runtime**: Python 3.11
- **Container Platform**: Google Cloud Run
- **Message Queue**: Google Cloud Pub/Sub
- **Database**: Firestore (NoSQL) for chat history, Cloud SQL (Postgres) for Django frontend
- **Secrets Management**: Google Secret Manager
- **CI/CD**: Google Cloud Build with GitHub integration

## Services

### 1. Webhook Listener (`vocoeng-webhook-listener`)
- Flask-based service for receiving external webhooks
- Handles WhatsApp, API integrations
- Publishes messages to Pub/Sub for processing

### 2. Processing Worker (`vocoeng-worker`)
- AI processing and external API calls
- Subscribes to Pub/Sub messages
- Integrates with OpenAI and other AI services
- Updates Firestore with processing results

### 3. Django Frontend (`vocoeng-django-frontend`)
- Django REST Framework API
- Admin dashboard for analytics
- Cloud SQL integration for structured data
- Firestore integration for chat history

## Quick Start

Each service has its own deployment configuration:

```bash
# Deploy webhook listener
cd vocoeng-webhook-listener
gcloud builds submit --config cloudbuild.yaml

# Deploy processing worker
cd vocoeng-worker
gcloud builds submit --config cloudbuild.yaml

# Deploy Django frontend
cd vocoeng-django-frontend
gcloud builds submit --config cloudbuild.yaml
```

## Environment Variables

All services use environment variables for configuration. Key variables include:

- `PROJECT_ID`: GCP Project ID
- `PUBSUB_TOPIC`: Pub/Sub topic name
- `FIRESTORE_PROJECT`: Firestore project ID
- `SECRET_MANAGER_SECRETS`: Comma-separated secret names

## Security

- All secrets stored in Google Secret Manager
- IAM roles configured for inter-service authentication
- No hardcoded credentials or API keys
- Secure container images with minimal attack surface

## Monitoring

- Cloud Run provides built-in monitoring and logging
- Structured logging for all services
- Error tracking and performance metrics

## Contributing

Each service is independently deployable. Follow the microservices pattern:
1. Make changes to the specific service
2. Test locally using Docker
3. Push to GitHub (triggers Cloud Build)
4. Monitor deployment in Cloud Console

For detailed setup instructions, see individual service README files.
