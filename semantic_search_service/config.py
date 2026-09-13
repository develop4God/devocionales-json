"""12-factor config for the semantic search service: env vars (optionally
via a .env file) are the source of truth, with the existing repo-relative
layout as the only hardcoded fallback — so a deployment, container, or
packaged install can repoint every path without touching code.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SEMANTIC_SEARCH_", env_file=".env", extra="ignore")

    data_dir: Path = ROOT / "editorial" / "semantic_search"
    model_name: str = "BAAI/bge-m3"


settings = Settings()
