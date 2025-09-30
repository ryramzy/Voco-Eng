"""
VocoEng Webhook Listener Service

A Flask application that receives external webhooks (WhatsApp, APIs) and publishes
messages to Pub/Sub for processing by the worker service.

Architecture:
- Stateless design for horizontal scaling
- Event-driven communication via Pub/Sub
- Secure secret management via Secret Manager
- Structured logging for monitoring
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from flask import Flask, request, jsonify, abort
from google.cloud import pubsub_v1
from google.cloud import secretmanager
import structlog
import pydantic

# Configure structured logging for Cloud Run
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize Flask app
app = Flask(__name__)

# Environment variables with defaults for local development
PROJECT_ID = os.getenv('PROJECT_ID', 'vocoeng-dev')
PUBSUB_TOPIC = os.getenv('PUBSUB_TOPIC', 'vocoeng-messages')
SECRET_NAME = os.getenv('SECRET_NAME', 'webhook-secrets')

# Initialize Google Cloud clients
publisher = pubsub_v1.PublisherClient()
secret_client = secretmanager.SecretManagerServiceClient()


class WebhookMessage(pydantic.BaseModel):
    """Pydantic model for webhook message validation"""
    source: str  # e.g., 'whatsapp', 'api', 'telegram'
    user_id: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = {}


class WebhookResponse(pydantic.BaseModel):
    """Response model for webhook endpoints"""
    status: str
    message: str
    message_id: Optional[str] = None


def get_secret(secret_name: str, version: str = "latest") -> str:
    """
    Retrieve secret from Google Secret Manager
    
    Args:
        secret_name: Name of the secret
        version: Version of the secret (default: latest)
    
    Returns:
        Secret value as string
    
    Raises:
        Exception: If secret retrieval fails
    """
    try:
        name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/{version}"
        response = secret_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error("Failed to retrieve secret", secret_name=secret_name, error=str(e))
        raise


def publish_to_pubsub(message_data: Dict[str, Any]) -> str:
    """
    Publish message to Pub/Sub topic for worker processing
    
    Args:
        message_data: Dictionary containing message data
    
    Returns:
        Message ID from Pub/Sub
    
    Raises:
        Exception: If publishing fails
    """
    try:
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
        
        # Serialize message data
        message_json = json.dumps(message_data, default=str)
        message_bytes = message_json.encode('utf-8')
        
        # Publish message
        future = publisher.publish(topic_path, message_bytes)
        message_id = future.result()
        
        logger.info("Message published to Pub/Sub", 
                   message_id=message_id, 
                   topic=PUBSUB_TOPIC)
        
        return message_id
        
    except Exception as e:
        logger.error("Failed to publish to Pub/Sub", error=str(e))
        raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "service": "vocoeng-webhook-listener",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """
    WhatsApp webhook endpoint
    
    Receives WhatsApp messages and forwards them to Pub/Sub for processing.
    Validates webhook signature for security.
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            abort(400, description="No JSON data provided")
        
        # Validate webhook signature (implement based on WhatsApp requirements)
        # signature = request.headers.get('X-Hub-Signature-256')
        # if not verify_whatsapp_signature(signature, request.data):
        #     abort(401, description="Invalid signature")
        
        # Extract message data
        user_id = data.get('from', '')
        message_text = data.get('text', {}).get('body', '')
        timestamp = datetime.utcnow()
        
        if not user_id or not message_text:
            abort(400, description="Missing required fields: from, text.body")
        
        # Create webhook message
        webhook_msg = WebhookMessage(
            source='whatsapp',
            user_id=user_id,
            message=message_text,
            timestamp=timestamp,
            metadata={
                'whatsapp_data': data,
                'received_at': timestamp.isoformat()
            }
        )
        
        # Publish to Pub/Sub
        message_id = publish_to_pubsub(webhook_msg.dict())
        
        logger.info("WhatsApp webhook processed", 
                   user_id=user_id, 
                   message_id=message_id)
        
        return jsonify(WebhookResponse(
            status="success",
            message="Message received and queued for processing",
            message_id=message_id
        ).dict())
        
    except Exception as e:
        logger.error("WhatsApp webhook error", error=str(e))
        abort(500, description="Internal server error")


@app.route('/webhook/api', methods=['POST'])
def api_webhook():
    """
    Generic API webhook endpoint
    
    Receives messages from external APIs and forwards them to Pub/Sub.
    Supports authentication via API key stored in Secret Manager.
    """
    try:
        # Validate API key
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            abort(401, description="Missing API key")
        
        # Get valid API key from Secret Manager
        valid_api_key = get_secret('api-webhook-key')
        if api_key != valid_api_key:
            abort(401, description="Invalid API key")
        
        # Get request data
        data = request.get_json()
        if not data:
            abort(400, description="No JSON data provided")
        
        # Extract required fields
        user_id = data.get('user_id', '')
        message = data.get('message', '')
        source = data.get('source', 'api')
        timestamp = datetime.utcnow()
        
        if not user_id or not message:
            abort(400, description="Missing required fields: user_id, message")
        
        # Create webhook message
        webhook_msg = WebhookMessage(
            source=source,
            user_id=user_id,
            message=message,
            timestamp=timestamp,
            metadata={
                'api_data': data,
                'received_at': timestamp.isoformat(),
                'client_ip': request.remote_addr
            }
        )
        
        # Publish to Pub/Sub
        message_id = publish_to_pubsub(webhook_msg.dict())
        
        logger.info("API webhook processed", 
                   user_id=user_id, 
                   source=source,
                   message_id=message_id)
        
        return jsonify(WebhookResponse(
            status="success",
            message="Message received and queued for processing",
            message_id=message_id
        ).dict())
        
    except Exception as e:
        logger.error("API webhook error", error=str(e))
        abort(500, description="Internal server error")


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    return jsonify({
        "status": "error",
        "message": str(error.description)
    }), 400


@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors"""
    return jsonify({
        "status": "error",
        "message": str(error.description)
    }), 401


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    logger.error("Internal server error", error=str(error))
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500


if __name__ == '__main__':
    # For local development only
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
