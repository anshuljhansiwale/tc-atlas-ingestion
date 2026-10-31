from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Teamcenter
    tc_mode: str = Field(default="mock", description="mock | rest")
    tc_base_url: str = "https://teamcenter.example.com"
    tc_username: str = ""
    tc_password: str = ""
    tc_group: str = "dba"
    tc_role: str = "DBA"

    # Local filesystem for IGES
    cad_root: Path = Path("./data/iges")

    # MongoDB Atlas
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "cad_ingestion"
    mongodb_collection: str = "parts"

    # Atlas Automated Embedding (Voyage) — must match atlas/vector_index.json
    vector_index_name: str = "parts_vector_index"
    voyage_model: str = Field(
        default="voyage-4",
        description="voyage-4 | voyage-4-large | voyage-4-lite | voyage-code-4",
    )

    # Pipeline
    batch_size: int = 50
    log_level: str = "INFO"

    @field_validator("cad_root", mode="before")
    @classmethod
    def _expand_cad_root(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @field_validator("tc_mode", "voyage_model")
    @classmethod
    def _normalize_choice(cls, value: str) -> str:
        return value.strip().lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()
