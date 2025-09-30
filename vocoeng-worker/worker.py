"""
VocoEng Processing Worker Service

A Python application that processes messages from Pub/Sub, executes AI processing
and external API calls, then stores results in Firestore and publishes responses.

Architecture:
- Event-driven processing via Pub/Sub subscription
- Stateless design for horizontal scaling
- AI service integrations (OpenAI, Anthropic)
- Firestore for chat history persistence
- Response publishing back to Pub/Sub
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify
from google.cloud import pubsub_v1
from google.cloud import secretmanager
from google.cloud import firestore
import openai
import anthropic
import structlog
import pydantic
import requests
from celery import Celery

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

# Environment variables
PROJECT_ID = os.getenv('PROJECT_ID', 'vocoeng-dev')
PUBSUB_SUBSCRIPTION = os.getenv('PUBSUB_SUBSCRIPTION', 'vocoeng-messages-sub')
PUBSUB_TOPIC = os.getenv('PUBSUB_TOPIC', 'vocoeng-responses')

# Initialize Google Cloud clients
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()
secret_client = secretmanager.SecretManagerServiceClient()
db = firestore.Client(project=PROJECT_ID)

# Initialize AI clients
openai_client = None
anthropic_client = None


class ProcessingMessage(pydantic.BaseModel):
    """Pydantic model for processing message validation"""
    source: str
    user_id: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = {}


class AIResponse(pydantic.BaseModel):
    """Model for AI service responses"""
    response: str
    model: str
    usage: Optional[Dict[str, Any]] = {}
    metadata: Optional[Dict[str, Any]] = {}


class ProcessingResult(pydantic.BaseModel):
    """Model for processing results"""
    message_id: str
    user_id: str
    original_message: str
    ai_response: AIResponse
    processing_time_ms: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = {}


def get_secret(secret_name: str, version: str = "latest") -> str:
    """Retrieve secret from Google Secret Manager"""
    try:
        name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/{version}"
        response = secret_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error("Failed to retrieve secret", secret_name=secret_name, error=str(e))
        raise


def initialize_ai_clients():
    """Initialize AI service clients with secrets"""
    global openai_client, anthropic_client
    
    try:
        # Initialize OpenAI client
        openai_api_key = get_secret('openai-api-key')
        openai_client = openai.OpenAI(api_key=openai_api_key)
        
        # Initialize Anthropic client
        anthropic_api_key = get_secret('anthropic-api-key')
        anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        logger.info("AI clients initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize AI clients", error=str(e))
        raise


async def process_with_openai(message: str, user_context: Dict[str, Any]) -> AIResponse:
    """Process message using OpenAI GPT models"""
    try:
        if not openai_client:
            initialize_ai_clients()
        
        # Get conversation history from Firestore
        conversation_history = get_conversation_history(user_id=user_context.get('user_id', ''))
        
        # Prepare messages for OpenAI
        messages = []
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            role = "user" if msg.get('source') != 'ai' else "assistant"
            messages.append({"role": role, "content": msg.get('message', '')})
        
        messages.append({"role": "user", "content": message})
        
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        return AIResponse(
            response=ai_response,
            model="gpt-4",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            metadata={"provider": "openai"}
        )
        
    except Exception as e:
        logger.error("OpenAI processing failed", error=str(e))
        raise


async def process_with_anthropic(message: str, user_context: Dict[str, Any]) -> AIResponse:
    """Process message using Anthropic Claude models"""
    try:
        if not anthropic_client:
            initialize_ai_clients()
        
        # Get conversation history from Firestore
        conversation_history = get_conversation_history(user_id=user_context.get('user_id', ''))
        
        # Prepare conversation for Anthropic
        conversation_text = ""
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            if msg.get('source') != 'ai':
                conversation_text += f"Human: {msg.get('message', '')}\n"
            else:
                conversation_text += f"Assistant: {msg.get('message', '')}\n"
        
        conversation_text += f"Human: {message}\nAssistant:"
        
        # Call Anthropic API
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": conversation_text}]
        )
        
        ai_response = response.content[0].text
        
        return AIResponse(
            response=ai_response,
            model="claude-3-sonnet-20240229",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            metadata={"provider": "anthropic"}
        )
        
    except Exception as e:
        logger.error("Anthropic processing failed", error=str(e))
        raise


def get_conversation_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve conversation history from Firestore"""
    try:
        messages_ref = db.collection('conversations').document(user_id).collection('messages')
        docs = messages_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        history = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            history.append(data)
        
        return list(reversed(history))  # Return in chronological order
        
    except Exception as e:
        logger.error("Failed to get conversation history", user_id=user_id, error=str(e))
        return []


def save_message_to_firestore(message_data: Dict[str, Any], ai_response: AIResponse, processing_time_ms: int):
    """Save message and AI response to Firestore"""
    try:
        user_id = message_data.get('user_id')
        timestamp = datetime.now(timezone.utc)
        
        # Save original message
        messages_ref = db.collection('conversations').document(user_id).collection('messages')
        message_doc = {
            'source': message_data.get('source'),
            'user_id': user_id,
            'message': message_data.get('message'),
            'timestamp': timestamp,
            'metadata': message_data.get('metadata', {})
        }
        message_doc_ref = messages_ref.add(message_doc)[1]
        
        # Save AI response
        response_doc = {
            'source': 'ai',
            'user_id': user_id,
            'message': ai_response.response,
            'timestamp': timestamp,
            'model': ai_response.model,
            'usage': ai_response.usage,
            'processing_time_ms': processing_time_ms,
            'metadata': ai_response.metadata
        }
        response_doc_ref = messages_ref.add(response_doc)[1]
        
        # Update conversation summary
        conversation_ref = db.collection('conversations').document(user_id)
        conversation_ref.set({
            'last_activity': timestamp,
            'message_count': firestore.Increment(1),
            'last_message': message_data.get('message'),
            'last_response': ai_response.response
        }, merge=True)
        
        logger.info("Messages saved to Firestore", 
                   user_id=user_id,
                   message_id=message_doc_ref.id,
                   response_id=response_doc_ref.id)
        
        return {
            'message_id': message_doc_ref.id,
            'response_id': response_doc_ref.id
        }
        
    except Exception as e:
        logger.error("Failed to save to Firestore", error=str(e))
        raise


def publish_response_to_pubsub(result: ProcessingResult):
    """Publish processing result to response topic"""
    try:
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
        
        # Serialize result data
        result_json = json.dumps(result.dict(), default=str)
        result_bytes = result_json.encode('utf-8')
        
        # Publish result
        future = publisher.publish(topic_path, result_bytes)
        message_id = future.result()
        
        logger.info("Response published to Pub/Sub", 
                   message_id=message_id, 
                   topic=PUBSUB_TOPIC)
        
        return message_id
        
    except Exception as e:
        logger.error("Failed to publish response to Pub/Sub", error=str(e))
        raise


async def process_message(message_data: Dict[str, Any]) -> ProcessingResult:
    """Main message processing function"""
    start_time = datetime.now()
    
    try:
        # Validate message
        processing_msg = ProcessingMessage(**message_data)
        
        # Choose AI provider based on configuration or round-robin
        # For now, default to OpenAI
        ai_response = await process_with_openai(
            message=processing_msg.message,
            user_context={'user_id': processing_msg.user_id}
        )
        
        # Calculate processing time
        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Save to Firestore
        firestore_ids = save_message_to_firestore(
            message_data=message_data,
            ai_response=ai_response,
            processing_time_ms=processing_time_ms
        )
        
        # Create processing result
        result = ProcessingResult(
            message_id=firestore_ids['message_id'],
            user_id=processing_msg.user_id,
            original_message=processing_msg.message,
            ai_response=ai_response,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now(timezone.utc),
            metadata={
                'firestore_ids': firestore_ids,
                'source': processing_msg.source
            }
        )
        
        # Publish response
        publish_response_to_pubsub(result)
        
        logger.info("Message processed successfully", 
                   user_id=processing_msg.user_id,
                   processing_time_ms=processing_time_ms)
        
        return result
        
    except Exception as e:
        logger.error("Message processing failed", error=str(e))
        raise


def callback(message):
    """Pub/Sub message callback handler"""
    try:
        # Decode message
        message_data = json.loads(message.data.decode('utf-8'))
        
        logger.info("Received message for processing", 
                   message_id=message.message_id,
                   user_id=message_data.get('user_id'))
        
        # Process message asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(process_message(message_data))
            logger.info("Message processed successfully", 
                       user_id=result.user_id,
                       message_id=result.message_id)
        finally:
            loop.close()
        
        # Acknowledge message
        message.ack()
        
    except Exception as e:
        logger.error("Message processing failed", 
                    message_id=message.message_id, 
                    error=str(e))
        # Nack message to retry later
        message.nack()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "service": "vocoeng-worker",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/process', methods=['POST'])
def process_webhook():
    """Direct processing endpoint for testing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Process message
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(process_message(data))
            return jsonify(result.dict())
        finally:
            loop.close()
            
    except Exception as e:
        logger.error("Direct processing failed", error=str(e))
        return jsonify({"error": str(e)}), 500


def start_pubsub_listener():
    """Start Pub/Sub message listener"""
    try:
        subscription_path = subscriber.subscription_path(PROJECT_ID, PUBSUB_SUBSCRIPTION)
        
        # Configure streaming pull
        flow_control = pubsub_v1.types.FlowControl(max_messages=100)
        
        # Start listening
        streaming_pull_future = subscriber.pull(
            subscription_path,
            callback=callback,
            flow_control=flow_control
        )
        
        logger.info("Started Pub/Sub listener", subscription=PUBSUB_SUBSCRIPTION)
        
        # Keep the main thread alive
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            streaming_pull_future.result()
            
    except Exception as e:
        logger.error("Failed to start Pub/Sub listener", error=str(e))
        raise


if __name__ == '__main__':
    # Initialize AI clients
    initialize_ai_clients()
    
    # Start Pub/Sub listener in background
    import threading
    listener_thread = threading.Thread(target=start_pubsub_listener, daemon=True)
    listener_thread.start()
    
    # Run Flask app
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
