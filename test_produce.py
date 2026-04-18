import asyncio
from backend.config import get_settings
from backend.core.rabbitmq import init_rabbitmq, publish_article_task, close_rabbitmq

async def main():
    settings = get_settings()
    
    # Initialize connection to CloudAMQP
    print(f"Connecting to RabbitMQ...")
    await init_rabbitmq(settings.rabbitmq_url)
    
    # Simulate an ingestion task
    mock_article = {
        "url": "https://example-news.com/ai-breakthrough",
        "title": "AI Agents Now Working Autonomously",
        "text": "In a stunning breakthrough, AI agents can now seamlessly interact with cloud messaging queues..."
    }
    
    print(f"Publishing article task: {mock_article['url']}")
    await publish_article_task(mock_article)
    
    # Graceful shutdown
    await asyncio.sleep(1) # give it a moment to flush
    await close_rabbitmq()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
