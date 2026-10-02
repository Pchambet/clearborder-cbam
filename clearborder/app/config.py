"""Application settings, read from the environment or a local .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ClearBorder"
    app_version: str = "0.1.0"
    debug: bool = False  # True echoes every SQL statement

    database_url: str = "sqlite:///./clearborder.db"

    # Comma-separated API keys; empty = no authentication (local development).
    # Kept as a plain string: pydantic-settings would otherwise JSON-decode a list
    # field and reject the documented API_KEYS="key1,key2" form.
    api_keys: str = ""

    @property
    def allowed_api_keys(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    cbam_sectors: list[str] = [
        "iron_steel",
        "aluminium",
        "cement",
        "fertilisers",
        "hydrogen",
        "electricity",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
