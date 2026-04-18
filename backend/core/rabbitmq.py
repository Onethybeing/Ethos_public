import json
import logging
import aio_pika
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_connection: Optional[aio_pika.RobustConnection] = None
_channel: Optional[aio_pika.RobustChannel] = None

async def init_rabbitmq(url: str):
    """Initialize RabbitMQ connection and basic structure. Call on startup."""
    global _connection, _channel
    try:
        _connection = await aio_pika.connect_robust(url)
        _channel = await _connection.channel()
        logger.info("RabbitMQ connection established.")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")

async def close_rabbitmq():
    """Close RabbitMQ connection."""
    global _connection
    if _connection:
        await _connection.close()
        logger.info("RabbitMQ connection closed.")

async def publish_article_task(article_data: Dict[str, Any]):
    """Publish an article processing task to the queue."""
    global _channel
    if not _channel:
        logger.error("RabbitMQ channel not initialized.")
        return

    queue_name = "article_processing"
    # Ensure queue exists
    queue = await _channel.declare_queue(queue_name, durable=True)
    
    message = aio_pika.Message(
        body=json.dumps(article_data).encode("utf-8"),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
    )
    
    await _channel.default_exchange.publish(message, routing_key=queue.name)
    logger.debug(f"Published article task to {queue_name}: {article_data.get('url')}")
