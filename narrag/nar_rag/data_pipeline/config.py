# Data Pipeline Configuration
import os
from dotenv import load_dotenv

load_dotenv()

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
LLM_RATE_LIMIT_SECONDS = 0.5

# Embedding Models
DENSE_MODEL = "all-mpnet-base-v2"
DENSE_VECTOR_SIZE = 768
IMAGE_MODEL = "openai/clip-vit-base-patch32"
IMAGE_VECTOR_SIZE = 512

# Ingestion Settings
SIMILARITY_THRESHOLD = 0.90
VARIANT_THRESHOLD = 0.75
BATCH_SIZE = 100

# Data Sources
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://www.npr.org/rss/rss.php?id=1019",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
]

REDDIT_SUBREDDITS = ["technology", "Futurology", "science"]
REDDIT_LIMIT = 25

HN_LIMIT = 30
