from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./insightpilot.db"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]

    # Auth (Supabase)
    supabase_jwt_secret: str = ""
    supabase_url: str = ""

    # Uploads
    max_csv_size_mb: int = 50

    # Set True to skip JWT validation and use a fixed dev user
    dev_mode: bool = True

    # LLM
    gemini_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
