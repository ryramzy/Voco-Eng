# VocoEng Webhook Listener Service

A Flask-based microservice that receives external webhooks (WhatsApp, APIs) and publishes messages to Google Cloud Pub/Sub for processing by the worker service.

## Architecture

This service follows serverless best practices:

- **Stateless Design**: No local state or disk persistence
- **Event-Driven**: Uses Pub/Sub for decoupled messaging
- **Secure**: Secrets managed via Google Secret Manager
- **Scalable**: Designed for horizontal scaling on Cloud Run
- **Observable**: Structured logging for monitoring and debugging

## Features

- WhatsApp webhook integration
- Generic API webhook endpoint with authentication
- Pub/Sub message publishing
- Secret Manager integration
- Health check endpoint
- Request validation with Pydantic
- Structured logging

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_ID` | GCP Project ID | `vocoeng-dev` |
| `PUBSUB_TOPIC` | Pub/Sub topic name | `vocoeng-messages` |
| `SECRET_NAME` | Secret Manager secret name | `webhook-secrets` |
| `PORT` | Port for local development | `8080` |

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status.

### WhatsApp Webhook
```
POST /webhook/whatsapp
```
Receives WhatsApp messages and forwards them to Pub/Sub.

**Headers:**
- `Content-Type: application/json`

**Body:**
```json
{
  "from": "user_phone_number",
  "text": {
    "body": "message content"
  }
}
```

### API Webhook
```
POST /webhook/api
```
Generic webhook endpoint for external APIs.

**Headers:**
- `X-API-Key: your_api_key`
- `Content-Type: application/json`

**Body:**
```json
{
  "user_id": "unique_user_id",
  "message": "message content",
  "source": "api"
}
```

## Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set environment variables:**
```bash
export PROJECT_ID=your-gcp-project
export PUBSUB_TOPIC=vocoeng-messages
```

3. **Run locally:**
```bash
python app.py
```

4. **Test endpoints:**
```bash
# Health check
curl http://localhost:8080/health

# API webhook (with valid API key)
curl -X POST http://localhost:8080/webhook/api \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "message": "Hello world"}'
```

## Docker Development

1. **Build image:**
```bash
docker build -t vocoeng-webhook-listener .
```

2. **Run container:**
```bash
docker run -p 8080:8080 \
  -e PROJECT_ID=your-gcp-project \
  -e PUBSUB_TOPIC=vocoeng-messages \
  vocoeng-webhook-listener
```

## Deployment

The service is automatically deployed via Cloud Build when changes are pushed to the main branch.

### Manual Deployment

```bash
gcloud builds submit --config cloudbuild.yaml
```

### Required GCP Resources

1. **Pub/Sub Topic:**
```bash
gcloud pubsub topics create vocoeng-messages
```

2. **Service Account:**
```bash
gcloud iam service-accounts create vocoeng-webhook-listener
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vocoeng-webhook-listener@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vocoeng-webhook-listener@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

3. **Secrets:**
```bash
# API webhook key
echo -n "your-secure-api-key" | gcloud secrets create api-webhook-key --data-file=-
```

## Security Considerations

- All secrets stored in Google Secret Manager
- API key authentication for generic webhook
- WhatsApp signature validation (implement as needed)
- No hardcoded credentials
- Service account with minimal required permissions

## Monitoring

- Structured JSON logging for Cloud Logging
- Health check endpoint for monitoring
- Error tracking and alerting
- Performance metrics via Cloud Run

## Message Format

Messages published to Pub/Sub follow this schema:

```json
{
  "source": "whatsapp|api|telegram",
  "user_id": "unique_user_identifier",
  "message": "message content",
  "timestamp": "2024-01-01T12:00:00Z",
  "metadata": {
    "received_at": "2024-01-01T12:00:00Z",
    "client_ip": "192.168.1.1",
    "additional_data": {}
  }
}
```
