from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class ProviderConfig(BaseModel):
    base_url: str
    port: int

class EnrichmentConfig(BaseModel):
    model_id: str
    port: int
    use_bearer_model_id: bool = True
    max_batch_size: int = 5

class Settings(BaseSettings):
    marvin_host: str
    providers: List[ProviderConfig]
    cache_ttl_seconds: int = 300
    refresh_interval_seconds: int = 60
    enrichment: EnrichmentConfig
    timeout_fetch_models_seconds: int = 10
    timeout_enrich_models_seconds: int = 60

    model_config = SettingsConfigDict(env_prefix="LLM_", yaml_file="config.yaml")

settings = Settings()  # auto-loads from env + config.yaml
