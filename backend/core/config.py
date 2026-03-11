from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

# Absolute path to the backend/ directory (where this file lives).
# This ensures the SQLite DB is always found at backend/insightpilot.db
# regardless of which directory uvicorn is launched from.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB_URL = f"sqlite:///{(_BACKEND_DIR / 'insightpilot.db').as_posix()}"


class Settings(BaseSettings):
    # Database — defaults to an absolute path so it works from any cwd
    database_url: str = _DEFAULT_DB_URL

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "https://insightspilot.vercel.app"
    ]

    # Auth (Supabase)
    supabase_jwt_secret: str = ""
    supabase_url: str = ""

    # Uploads
    max_csv_size_mb: int = 50

    # Set True to skip JWT validation and use a fixed dev user
    dev_mode: bool = True

    # LLM
    gemini_api_key: str = ""
    groq_api_key: str = ""

    class Config:
        env_file = str(_BACKEND_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
