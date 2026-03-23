# Agents Module Configuration

# Mutation Detection
MUTATION_SIBLING_LIMIT = 5
MUTATION_DESCENDANT_LIMIT = 10

# Outcome Tracing
OUTCOME_HISTORICAL_CUTOFF_DAYS = 90
OUTCOME_FORWARD_WINDOW_START_DAYS = 7
OUTCOME_FORWARD_WINDOW_END_DAYS = 120

# Evolution Analysis
EVOLUTION_WINDOWS = {
    "T0": 180,  # 6 months ago
    "T1": 90,   # 3 months ago
    "T2": 30,   # 1 month ago
    "T3": 0,    # Current
}

# Dominance Thresholds
DOMINANT_PREVALENCE_THRESHOLD = 0.4
RISING_VELOCITY_THRESHOLD = 2.0
ECHO_CHAMBER_DIVERSITY_THRESHOLD = 0.3

# Enrichment Agent
ENRICHMENT_BATCH_SIZE = 20
ENRICHMENT_SCRAPE_TIMEOUT = 3.0
ENRICHMENT_MAX_ATTEMPTS = 3  # Max retry attempts per article before giving up

# Adaptive Rate Limiting
ENRICHMENT_BASE_DELAY = 4        # Initial delay between batches (seconds)
ENRICHMENT_MAX_DELAY = 120       # Maximum backoff delay (seconds)
ENRICHMENT_BACKOFF_FACTOR = 2.0  # Multiply delay by this on 429
ENRICHMENT_COOLDOWN_FACTOR = 0.7 # Multiply delay by this on success

# Priority Enrichment
ENRICHMENT_PRIORITY_TOPICS = []  # e.g. ["AI", "climate"] — enriched first
ENRICHMENT_PRIORITY_RECENCY_HOURS = 24  # Articles newer than this get priority
