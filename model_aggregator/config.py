MARVIN_HOST = "http://10.7.2.100"
PORTS = [8080, 8090, 11434]

CACHE_TTL = 300  # seconds for /api/models responses

# Brain / enrichment model configuration
ENRICH_MODEL_ID = "unsloth/GLM-4.6-GGUF:UD-IQ2_XXS"
ENRICH_PORT = 8080

# Only for brain calls on ENRICH_PORT we send Bearer=<model_id> as API key
USE_BEARER_ON_ENRICH_PORT = True
