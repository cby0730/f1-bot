from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="F1BOT_",
        extra="ignore",
        populate_by_name=True,
    )

    # Required — no prefix (read directly from env)
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")

    # Optional — no prefix (read directly from env)
    telegram_proxy: str | None = Field(default=None, alias="TELEGRAM_PROXY")
    telegram_connect_timeout: float = Field(default=20.0, alias="TELEGRAM_CONNECT_TIMEOUT")
    telegram_read_timeout: float = Field(default=20.0, alias="TELEGRAM_READ_TIMEOUT")

    # Database — prefix: F1BOT_DATABASE_URL
    database_url: str = "postgresql://mango:mango@localhost:31050/mango"

    # Logging — prefix: F1BOT_LOG_LEVEL, F1BOT_LOG_FORMAT
    log_level: str = "INFO"
    log_format: str = "auto"

    # API base URLs
    jolpica_base_url: str = "https://api.jolpi.ca/ergast/f1"
    openf1_base_url: str = "https://api.openf1.org/v1"

    # API rate limits
    jolpica_rate_per_second: float = 4.0
    jolpica_rate_per_hour: int = 500
    openf1_rate_per_second: float = 3.0
    openf1_rate_per_minute: int = 30

    # Notification rate limit
    notification_rate_per_second: float = 25.0
