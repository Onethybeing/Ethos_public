import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from backend.core.db.postgres import AsyncSessionLocal, Article
from backend.core.clients import get_encoder
from sentence_transformers import util
from sqlalchemy import select

CATEGORY_DEFS = {
    "Technology": "Technology Software AI Startups Gadgets Computing Engineering Internet",
    "Finance": "Finance Markets Economy Stocks Banking Crypto Business Investment",
    "Science": "Science Physics Biology Space Astronomy Research Chemistry",
    "Politics": "Politics Government Elections Policies Diplomacy Congress Law",
    "Health": "Health Medicine Wellness Healthcare Disease Fitness Diet",
    "Policy": "Policy Regulation Law Governance Legislation Public Affairs Rules",
}

async def main():
    encoder = get_encoder()
    
    cats = list(CATEGORY_DEFS.keys())
    cat_texts = list(CATEGORY_DEFS.values())
    
    print("Embedding categories...")
    # Generate embeddings for our categories
    cat_emb = encoder.encode(cat_texts, convert_to_tensor=True)
    
    print("Connecting to Postgres...")
    async with AsyncSessionLocal() as session:
        # Get all articles to categorize them
        query = select(Article)
        result = await session.execute(query)
        articles = result.scalars().all()
        
        print(f"Found {len(articles)} articles. Assigning categories...")
        updated_count = 0
        
        # Process in batches
        batch_size = 32
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            
            texts = []
            for a in batch:
                title = a.title or ""
                # Use title and the first 500 characters of content
                content = (a.content or "")[:500]
                texts.append(f"{title}. {content}")
                
            # Embed articles
            art_emb = encoder.encode(texts, convert_to_tensor=True)
            
            # Compute cosine similarities between articles and categories
            # sims shape: (batch_size, num_categories)
            sims = util.cos_sim(art_emb, cat_emb)
            
            # Find the best matching category for each article
            for j, a in enumerate(batch):
                best_idx = sims[j].argmax().item()
                # We can also check sims[j].max().item() if we want a threshold
                best_cat = cats[best_idx]
                
                if a.category != best_cat:
                    a.category = best_cat
                    updated_count += 1
                
        if updated_count > 0:
            print(f"Updating {updated_count} articles in DB...")
            await session.commit()
            print("Successfully updated database.")
        else:
            print("No articles to update.")

if __name__ == "__main__":
    asyncio.run(main())
