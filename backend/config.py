from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "EthosNews API"
    environment: str = "development"
    
    # LLM Settings
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    
    # Database Settings
    database_url: str = "sqlite:///./ethos.db"

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings():
    return Settings()
