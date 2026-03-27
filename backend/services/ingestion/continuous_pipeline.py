import os
import time
import asyncio
import uuid
from datetime import datetime, timedelta, UTC

import gdelt
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import spacy

from backend.core.db.postgres import save_article, init_db

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
load_dotenv(r"C:\Users\soura\ethos\Ethos\backend\.env")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "news_articles_streaming"

# Global Models
qdrant = None
encoder = None
nlp = None

def init_services():
    global qdrant, encoder, nlp
    print("\n[Init] Setting up Models and Qdrant...")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    try:
        qdrant.get_collection(collection_name=COLLECTION_NAME)
    except Exception:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    encoder = SentenceTransformer('all-MiniLM-L6-v2')
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        from spacy.cli import download
        download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")

# ---------------------------------------------------------
# Streaming Pipeline Steps
# ---------------------------------------------------------

async def fetch_gdelt_source(queue: asyncio.Queue):
    """
    Acts as our continuously polling Source (equivalent to a Pathway stream input).
    """
    g = gdelt.gdelt()
    seen_urls = set()
    
    while True:
        print(f"\n[Source] Polling GDELT at {datetime.now().strftime('%H:%M:%S')}...", flush=True)
        try:
            # Dynamically generated date to pull truly new articles 
            # Note: GDELT events have 15-minute delays; polling older blocks is safer or just today's specific datestring
            today_str = datetime.now(UTC).strftime('%Y %b %d')
            df = g.Search([today_str], table='events', coverage=True)
            if df is not None and not df.empty:
                urls = df['SOURCEURL'].dropna().unique().tolist()
                timestamps = df['DATEADDED'].tolist()
                
                new_count = 0
                for url, ts in zip(urls, timestamps):
                    if url not in seen_urls:
                        seen_urls.add(url)
                        new_count += 1
                        # Push to the streaming pipeline
                        await queue.put({"source": url, "timestamp": str(ts)})
                        
                print(f"[Source] Found {new_count} NEW articles. Pushing to stream...")
            else:
                print("[Source] No new events found currently.")
        except Exception as e:
            print(f"[Source] Error polling GDELT: {e}")
            
        # Poll again every 60 seconds
        await asyncio.sleep(60)

async def stream_processor(queue: asyncio.Queue):
    """
    Acts as our UDF mapper and sink. 
    Continuously listens for URLs and writes to Qdrant.
    """
    while True:
        # Wait for the next article in the stream
        article = await queue.get()
        url = article['source']
        
        try:
            # 1. Scrape (UDF)
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = ' '.join([p.get_text() for p in soup.find_all('p') if p.get_text().strip()])
            
            if not text.strip():
                continue # drop empty articles
                
            # 2. NER Processing (UDF)
            doc = nlp(text[:100000])
            entities = list(dict.fromkeys([ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "LOC"]]))
            
            # 3. Generating Embedding Vector (UDF)
            vector = encoder.encode(text).tolist()
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))

            # 4. Sink to Qdrant (Sink)
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={
                        "title": soup.find('title').get_text().strip() if soup.find('title') else "Untitled",
                        "source": url,
                        "timestamp": article['timestamp'],
                        "content": text,
                        "entities": entities
                    }
                )]
            )
            
            # 5. Sink to Permanent PostgreSQL Storage
            await save_article({
                "id": doc_id,  # Use same UUID as Qdrant to link records cleanly if needed
                "title": soup.find('title').get_text().strip() if soup.find('title') else "Untitled",
                "content": text,
                "url": url,
                "source": url, # Using URL directly as source if empty, or can parse domains
                "published_at": article['timestamp'], 
                "image_url": None,
                "category": None
            })

            print(f"[Sink] Streamed -> Qdrant & Postgres: {url[:60]}...")
            
        except Exception as e:
            # Silently catch 403s / timeouts and drop from stream to keep running 
            pass
        finally:
            queue.task_done()

# ---------------------------------------------------------
# Application Entrypoint
# ---------------------------------------------------------
async def main():
    print("========================================")
    print("   Continuous Ingestion Stream Started  ")
    print("========================================")
    
    # Init strict database migrations
    await init_db()
    
    init_services()
    
    # Pathway-like unbounded stream queue
    stream_queue = asyncio.Queue()
    
    # Run the poller and the processor concurrently
    await asyncio.gather(
        fetch_gdelt_source(stream_queue),
        stream_processor(stream_queue),
        stream_processor(stream_queue), # Run 2 parallel workers (scraping is slow)
        stream_processor(stream_queue)  # Total 3 workers
    )

if __name__ == "__main__":
    # Ensure Windows asyncio works cleanly
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown signal received. Stopping stream.")