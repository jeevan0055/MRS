from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# Get the backend directory to store SQLite DB there
BACKEND_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'cinematch.db'}")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-for-local-dev-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")

    class Config:
        env_file = ".env"


settings = Settings()
