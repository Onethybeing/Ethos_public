import json
import logging
from datetime import datetime
from typing import Optional
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

# Singleton producer instance
_producer: Optional[AIOKafkaProducer] = None

async def init_kafka_producer(broker_url: str = 'localhost:9092'):
    """Initialize the Kafka Producer. Call this during FastAPI startup."""
    global _producer
    try:
        _producer = AIOKafkaProducer(bootstrap_servers=broker_url)
        await _producer.start()
        logger.info("AIOKafka producer initialized and started.")
    except Exception as e:
        logger.error(f"Failed to initialize Kafka producer: {e}")

async def close_kafka_producer():
    """Close the Kafka Producer. Call this during FastAPI shutdown."""
    global _producer
    if _producer:
        await _producer.stop()
        logger.info("AIOKafka producer stopped.")

async def stream_event(user_id: str, article_id: str, action: str, category: str):
    """Publish an engagement event to Kafka."""
    global _producer
    if not _producer:
        logger.warning("Kafka producer not initialized. Skipping event stream.")
        return

    event = {
        "user_id": user_id,
        "article_id": article_id,
        "action": action,      # e.g., "READ", "UPVOTE", "DWELL"
        "category": category,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        await _producer.send_and_wait("user-events", json.dumps(event).encode('utf-8'))
        logger.debug(f"Event streamed: {event}")
    except Exception as e:
        logger.error(f"Failed to stream event to Kafka: {e}")
