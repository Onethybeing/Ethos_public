import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
load_dotenv(r"C:\Users\soura\ethos\factchecker\.env")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# We will apply this to the actively streaming collection 
# so it immediately benefits the background pipeline!
COLLECTION_NAME = "news_articles_streaming" 

def setup_qdrant():
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # 1. Create or Verify Collection exists
    try:
        qdrant.get_collection(collection_name=COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' already exists (running from continuous stream).")
        print("Continuing to index application...")
    except Exception:
        print(f"Creating collection '{COLLECTION_NAME}' with size 384 and COSINE distance...")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    # 2. Add Payload Indexes
    print("\nApplying Payload Indexes live (without stopping ingestion)...")
    
    # 2a. entities -> allows fast exact-match lookup on the list of Named Entities
    qdrant.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="entities",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    print(" ✅ Indexed: 'entities' (Type: KEYWORD)")

    # 2b. source -> fast filtering by publisher / URL
    qdrant.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="source",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    print(" ✅ Indexed: 'source' (Type: KEYWORD)")

    # 2c. timestamp -> allows temporal searches (less than / greater than x date)
    qdrant.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="timestamp",
        field_schema=PayloadSchemaType.DATETIME,
    )
    print(" ✅ Indexed: 'timestamp' (Type: DATETIME)")

    print("\nQdrant Collection & Index setup complete! ✨")

if __name__ == "__main__":
    setup_qdrant()