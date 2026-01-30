from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "lia-delivery"
    env: str = "dev"
    log_level: str = "INFO"
    timezone: str = "America/Sao_Paulo"

    database_url: str = Field("postgresql+psycopg://postgres:postgres@localhost:5432/lia", alias="DATABASE_URL")

    evolution_base_url: str = Field("", alias="EVOLUTION_BASE_URL")
    evolution_api_key: str = Field("", alias="EVOLUTION_API_KEY")
    evolution_instance: str = Field("", alias="EVOLUTION_INSTANCE")

    saipos_base_url: str = Field("https://order-api.saipos.com", alias="SAIPOS_BASE_URL")
    saipos_partner_id: str = Field("", alias="SAIPOS_PARTNER_ID")
    saipos_partner_secret: str = Field("", alias="SAIPOS_PARTNER_SECRET")
    saipos_token_ttl_seconds: int = Field(3500, alias="SAIPOS_TOKEN_TTL_SECONDS")
    saipos_cod_store: str = Field("", alias="SAIPOS_COD_STORE")
    saipos_display_id: str = Field("", alias="SAIPOS_DISPLAY_ID")
    saipos_dry_run: bool = Field(False, alias="SAIPOS_DRY_RUN")

    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_model_chat: str = Field("gpt-4o-mini", alias="OPENAI_MODEL_CHAT")
    openai_model_embed: str = Field("text-embedding-3-small", alias="OPENAI_MODEL_EMBED")
    openai_model_transcribe: str = Field("whisper-1", alias="OPENAI_MODEL_TRANSCRIBE")

    google_maps_api_key: str = Field("", alias="GOOGLE_MAPS_API_KEY")
    delivery_city: str = Field("Itajaí", alias="DELIVERY_CITY")
    delivery_state: str = Field("SC", alias="DELIVERY_STATE")
    delivery_country: str = Field("BR", alias="DELIVERY_COUNTRY")

    client_id: str = Field("06a81600-26fc-472b-880e-e6293943354e", alias="CLIENT_ID")
    restaurant_name: str = Field("Marcio Lanches & Pizzas", alias="RESTAURANT_NAME")

    followup_interval_minutes: int = Field(2, alias="FOLLOWUP_INTERVAL_MINUTES")
    followup_enabled: bool = Field(True, alias="FOLLOWUP_ENABLED")

    # Behavior toggles
    debounce_wait_seconds: int = Field(10, alias="DEBOUNCE_WAIT_SECONDS")


settings = Settings()
