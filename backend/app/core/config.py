"""
Goldmine AI — Core Configuration

Loads environment variables and provides typed settings for the application.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"

# Pydantic reads .env values into Settings, while Prisma reads os.environ.
# Load the same root file before Prisma is imported; preserve process-env priority.
load_dotenv(ENV_FILE, override=False)


class Settings(BaseSettings):
    # Hugging Face
    hf_token: str = Field(default="", alias="HF_TOKEN")

    # Supabase
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    # Prisma/PostgreSQL. DIRECT_URL is used by schema tooling; runtime connects via DATABASE_URL.
    database_url: str = Field(default="", alias="DATABASE_URL")
    direct_url: str = Field(default="", alias="DIRECT_URL")

    # Optional: Web verification
    search_api_key: Optional[str] = Field(default=None, alias="SEARCH_API_KEY")

    # Google Gemini
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    synthesis_model_id: Optional[str] = Field(default=None, alias="SYNTHESIS_MODEL_ID")

    # Free inference is the safe default; paid providers stay hidden unless explicitly enabled.
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    free_models_only: bool = Field(default=True, alias="FREE_MODELS_ONLY")

    # Server
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:3000"]
    )

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def is_hf_configured(self) -> bool:
        return bool(self.hf_token)

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.google_api_key)

    @property
    def is_openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def is_supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def is_database_configured(self) -> bool:
        return bool(self.database_url)


settings = Settings()
