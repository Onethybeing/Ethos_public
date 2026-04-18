import asyncio
import json
import logging
import aio_pika

from backend.config import get_settings

logger = logging.getLogger(__name__)

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body)
            url = data.get('url', 'Unknown URL')
            logger.info(f"Processing heavy article ingestion task: {url}")
            
            # Example: 1. Run LLM Slop Detection
            # slop_status = await determine_slop(data['text'])
            
            # Example: 2. Run LLM Fact Checking
            # claims = await verify_claims(data['text'])
            
            # Example: 3. Vectorize and save to Postgres / Qdrant
            # await save_to_db(data, slop_status, claims)
            
            logger.info(f"Completed ingestion for: {url}")
        except Exception as e:
            logger.error(f"Error processing article: {e}")

async def start_worker():
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    # Ensuring the channel guarantees persistent queue tasks
    queue = await channel.declare_queue("article_processing", durable=True)
    
    logger.info("RabbitMQ Article Worker initialized. Listening for tasks...")
    await queue.consume(process_message)
    
    # Run forever
    await asyncio.Future()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_worker())
