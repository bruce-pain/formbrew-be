import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Class to hold application's config values."""

    model_config = SettingsConfigDict(env_file=".env")
    SECRET_KEY: str
    ALGORITHM: str
    ENVIRONMENT: str
    ACCESS_TOKEN_EXPIRY: int
    REFRESH_TOKEN_EXPIRY: int

    # Database configurations
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str
    DATABASE_TYPE: str

    # Test Database configurations
    TEST_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/test_db"

    # groq api key
    GROQ_API_KEY: str

    # Google Client ID
    GOOGLE_CLIENT_ID: str = ""

    # Google Sheets export OAuth client
    GOOGLE_SHEETS_CLIENT_ID: str = ""
    GOOGLE_SHEETS_CLIENT_SECRET: str = ""
    # Required encryption key for the stored refresh token.
    # Generate with: uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Must stay stable across restarts — rotating orphans stored tokens!
    GOOGLE_SHEETS_TOKEN_ENCRYPTION_KEY: str = ""

    # Directories
    MEDIA_DIR: str = os.path.join(BASE_DIR, "media")
    STATIC_DIR: str = os.path.join(BASE_DIR, "static")
    TEMPLATES_DIR: str = os.path.join(BASE_DIR, "templates")

    @property
    def database_url(self) -> str:
        """Dynamically construct DATABASE_URL"""
        return f"{self.DATABASE_TYPE}://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"


settings = Settings()
