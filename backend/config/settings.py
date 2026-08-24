"""
Application settings — loaded from environment variables.
Copy .env.example to .env and fill in your values.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str

    # Neo4j Aura (LearnGPS dedicated instance)
    neo4j_uri: str          # e.g. neo4j+s://xxxxxxxx.databases.neo4j.io
    neo4j_username: str     # usually "neo4j"
    neo4j_password: str

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Qdrant (replaced by ChromaDB in Day 6b — kept optional for backward compat)
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # Langfuse (AI observability)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # App
    app_env: str = "development"  # development | production
    max_tool_rounds: int = 3       # Hard limit per agent turn

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
