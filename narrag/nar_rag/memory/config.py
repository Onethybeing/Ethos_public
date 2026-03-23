# Memory Module Configuration
import os
from dotenv import load_dotenv

load_dotenv()

# Qdrant Settings
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_local_storage")

COLLECTION_NAME = "narrative_memory"

# Vector Dimensions
DENSE_VECTOR_SIZE = 768
IMAGE_VECTOR_SIZE = 512

# Search Defaults
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_SCORE_THRESHOLD = 0.3

# Decay Settings
DECAY_LAMBDA = 0.01  # Decay rate per day
FADE_THRESHOLD = 0.5
