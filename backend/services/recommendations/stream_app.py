import json
import logging
import faust
import redis.asyncio as redis_async
from backend.config import get_settings

settings = get_settings()

app = faust.App(
    'ethos-recommendation-streams',
    broker=f'kafka://{settings.kafka_broker_url}',
    store='rocksdb://',
)

# Connect to Redis to share state with FastAPI
redis_client = redis_async.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

class EngagementEvent(faust.Record, serializer='json'):
    user_id: str
    article_id: str
    action: str
    category: str
    timestamp: str

events_topic = app.topic('user-events', value_type=EngagementEvent)

# State Store: Keeps track of {"category": score} per user
user_profiles = app.Table('user-profiles', default=dict)

@app.agent(events_topic)
async def process_engagement(stream):
    """
    Process every incoming engagement event as it arrives via Kafka.
    Maintains a rolling state of category interests per user.
    """
    async for event in stream:
        # Determine weight of interaction
        weight = 0
        if event.action == "UPVOTE":
            weight = 2
        elif event.action == "READ":
            weight = 1
        elif event.action == "DOWNVOTE":
            weight = -1
        
        if weight == 0 or not event.category:
            continue

        # Get current user profile from the Faust state store
        profile = user_profiles[event.user_id]
        
        # Increment category affinity
        current_score = profile.get(event.category, 0)
        profile[event.category] = current_score + weight
        
        # Save back to state store
        user_profiles[event.user_id] = profile
        
        logging.info(f"Updated profile for User {event.user_id}: {profile}")
        
        # Publish profile update to Redis so the FastAPI endpoints can read it instantly
        # Key pattern: `user_profile:{user_id}`
        await redis_client.set(f"user_profile:{event.user_id}", json.dumps(profile))

if __name__ == '__main__':
    app.main()
