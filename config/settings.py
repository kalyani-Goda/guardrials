import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings - Google API for LLM, everything else local"""

    # ====== LLM: Google Generative AI ======
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")

    # ====== Local Database: SQLite ======
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./medi_triage.db"
    )

    # ====== Local Cache: Redis ======
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_TIMEOUT: int = int(os.getenv("REDIS_TIMEOUT", "5"))
    REDIS_MAX_RETRIES: int = int(os.getenv("REDIS_MAX_RETRIES", "3"))

    # ====== Local Vector Store: ChromaDB ======
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "chromadb")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./data/vector_store")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # ====== Presidio Configuration ======
    PRESIDIO_ANONYMIZER_THRESHOLD: float = float(
        os.getenv("PRESIDIO_ANONYMIZER_THRESHOLD", "0.5")
    )
    PII_ENTITIES_TO_DETECT: list = [
        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "SSN"
    ]

    # ====== JWT / Security ======
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    @property
    def secret_key(self) -> str:
        """Lowercase alias for SECRET_KEY for backward compatibility"""
        return self.SECRET_KEY

    # ====== EHR Integration (Optional) ======
    EHR_API_BASE_URL: str = os.getenv("EHR_API_BASE_URL", "http://localhost:8000")
    EHR_API_KEY: str = os.getenv("EHR_API_KEY", "")
    EHR_API_TIMEOUT: int = int(os.getenv("EHR_API_TIMEOUT", "30"))

    # ====== Ragas Faithfulness Threshold ======
    RAGAS_FAITHFULNESS_THRESHOLD: float = float(
        os.getenv("RAGAS_FAITHFULNESS_THRESHOLD", "0.95")
    )

    # ====== Logging ======
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # ====== Environment ======
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def get_database_url(self) -> str:
        """Get database connection URL"""
        return self.DATABASE_URL


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()