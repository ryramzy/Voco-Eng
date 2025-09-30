# VocoEng Processing Worker Service

A Python microservice that processes messages from Pub/Sub, executes AI processing and external API calls, then stores results in Firestore and publishes responses.

## Architecture

This service follows serverless best practices:

- **Event-Driven Processing**: Subscribes to Pub/Sub messages for processing
- **AI Integration**: Supports OpenAI GPT and Anthropic Claude models
- **Stateless Design**: No local state, designed for horizontal scaling
- **Firestore Integration**: Persists chat history and conversation state
- **Response Publishing**: Publishes processed results back to Pub/Sub

## Features

- Pub/Sub message subscription and processing
- AI service integrations (OpenAI, Anthropic)
- Firestore conversation history management
- Response publishing to Pub/Sub
- Structured logging and monitoring
- Health check endpoint
- Direct processing endpoint for testing

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_ID` | GCP Project ID | `vocoeng-dev` |
| `PUBSUB_SUBSCRIPTION` | Pub/Sub subscription name | `vocoeng-messages-sub` |
| `PUBSUB_TOPIC` | Response Pub/Sub topic | `vocoeng-responses` |
| `PORT` | Port for local development | `8080` |

## AI Providers

### OpenAI Integration
- Uses GPT-4 model by default
- Supports conversation history context
- Tracks token usage for cost monitoring

### Anthropic Integration
- Uses Claude-3-Sonnet model
- Maintains conversation context
- Tracks input/output token usage

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status.

### Direct Processing
```
POST /process
```
Process a message directly for testing purposes.

**Body:**
```json
{
  "source": "api",
  "user_id": "user123",
  "message": "Hello, how are you?",
  "timestamp": "2024-01-01T12:00:00Z",
  "metadata": {}
}
```

## Message Processing Flow

1. **Receive Message**: Subscribe to Pub/Sub messages
2. **Validate Data**: Use Pydantic for message validation
3. **Get Context**: Retrieve conversation history from Firestore
4. **AI Processing**: Call OpenAI or Anthropic APIs
5. **Store Results**: Save message and response to Firestore
6. **Publish Response**: Send result to response Pub/Sub topic
7. **Acknowledge**: Acknowledge original message

## Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set environment variables:**
```bash
export PROJECT_ID=your-gcp-project
export PUBSUB_SUBSCRIPTION=vocoeng-messages-sub
export PUBSUB_TOPIC=vocoeng-responses
```

3. **Set up secrets in Secret Manager:**
```bash
# OpenAI API key
echo -n "your-openai-key" | gcloud secrets create openai-api-key --data-file=-

# Anthropic API key
echo -n "your-anthropic-key" | gcloud secrets create anthropic-api-key --data-file=-
```

4. **Run locally:**
```bash
python worker.py
```

5. **Test processing:**
```bash
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api",
    "user_id": "test_user",
    "message": "Hello, how are you?",
    "timestamp": "2024-01-01T12:00:00Z"
  }'
```

## Docker Development

1. **Build image:**
```bash
docker build -t vocoeng-worker .
```

2. **Run container:**
```bash
docker run -p 8080:8080 \
  -e PROJECT_ID=your-gcp-project \
  -e PUBSUB_SUBSCRIPTION=vocoeng-messages-sub \
  -e PUBSUB_TOPIC=vocoeng-responses \
  vocoeng-worker
```

## Deployment

The service is automatically deployed via Cloud Build when changes are pushed to the main branch.

### Manual Deployment

```bash
gcloud builds submit --config cloudbuild.yaml
```

### Required GCP Resources

1. **Pub/Sub Subscription:**
```bash
gcloud pubsub subscriptions create vocoeng-messages-sub \
  --topic=vocoeng-messages \
  --ack-deadline=600
```

2. **Response Topic:**
```bash
gcloud pubsub topics create vocoeng-responses
```

3. **Service Account:**
```bash
gcloud iam service-accounts create vocoeng-worker
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
```

4. **Secrets:**
```bash
# OpenAI API key
echo -n "your-openai-key" | gcloud secrets create openai-api-key --data-file=-

# Anthropic API key
echo -n "your-anthropic-key" | gcloud secrets create anthropic-api-key --data-file=-
```

## Firestore Schema

### Conversations Collection
```
conversations/{user_id}
├── last_activity: timestamp
├── message_count: number
├── last_message: string
├── last_response: string
└── messages/{message_id}
    ├── source: string
    ├── user_id: string
    ├── message: string
    ├── timestamp: timestamp
    ├── model: string (for AI responses)
    ├── usage: object (for AI responses)
    ├── processing_time_ms: number (for AI responses)
    └── metadata: object
```

## Message Formats

### Input Message (from Pub/Sub)
```json
{
  "source": "whatsapp|api|telegram",
  "user_id": "unique_user_identifier",
  "message": "message content",
  "timestamp": "2024-01-01T12:00:00Z",
  "metadata": {
    "received_at": "2024-01-01T12:00:00Z",
    "client_ip": "192.168.1.1"
  }
}
```

### Output Response (to Pub/Sub)
```json
{
  "message_id": "firestore_message_id",
  "user_id": "unique_user_identifier",
  "original_message": "original message content",
  "ai_response": {
    "response": "AI generated response",
    "model": "gpt-4",
    "usage": {
      "prompt_tokens": 100,
      "completion_tokens": 50,
      "total_tokens": 150
    },
    "metadata": {
      "provider": "openai"
    }
  },
  "processing_time_ms": 2500,
  "timestamp": "2024-01-01T12:00:05Z",
  "metadata": {
    "firestore_ids": {
      "message_id": "msg_id",
      "response_id": "resp_id"
    },
    "source": "whatsapp"
  }
}
```

## Security Considerations

- All API keys stored in Google Secret Manager
- Service account with minimal required permissions
- No hardcoded credentials
- Secure container images
- Input validation with Pydantic

## Monitoring

- Structured JSON logging for Cloud Logging
- Processing time tracking
- Token usage monitoring
- Error tracking and alerting
- Performance metrics via Cloud Run

## Scaling

- Cloud Run automatically scales based on Pub/Sub message volume
- Stateless design allows horizontal scaling
- Configured for CPU-intensive AI processing
- Memory and CPU limits optimized for AI workloads
