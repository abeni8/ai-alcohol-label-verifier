from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    provider: Literal["demo", "openai"] = "demo"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1-mini"
    review_access_token: SecretStr = SecretStr("")
    ai_timeout_seconds: float = Field(default=12, ge=1, le=60)
    max_concurrent_requests: int = Field(default=3, ge=1, le=8)
    requests_per_minute: int = Field(default=180, ge=1, le=10000)
    dev_origin: str = "http://localhost:5173"

    @property
    def ready(self) -> bool:
        return self.provider == "demo" or bool(self.openai_api_key.get_secret_value())

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = MAX_IMAGES * MAX_IMAGE_BYTES + 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_BATCH_ROWS = 300
MAX_CSV_BYTES = 1_000_000
