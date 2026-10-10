from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

# Absolute path to the ResolveAI project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Central application configuration loaded from environment or .env file."""

    APP_NAME: str = Field(default="ResolveAI", description="Application name")
    APP_ENV: str = Field(default="development", description="Application environment (development, staging, production)")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    API_PREFIX: str = Field(default="/api/v1", description="Global API route prefix")
    DATABASE_URL: str = Field(
        default="sqlite:///./data/resolveai.db",
        description="SQLAlchemy database URL"
    )
    CHECKPOINT_DB_PATH: str = Field(
        default="./data/checkpoints.db",
        description="Dedicated SQLite database path for persistent LangGraph checkpoints (Level 5)"
    )
    LOG_LEVEL: str = Field(default="INFO", description="Application log level")
    PORT: int = Field(default=8000, description="Server listen port (Render environment provides PORT)")
    FRONTEND_URL: Optional[str] = Field(default=None, description="Production frontend URL for CORS")
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )

    # Optional AI Provider configuration (Level 2)
    LLM_PROVIDER: str = Field(default="none", description="AI Provider ('none', 'gemini', 'groq')")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Optional Google Gemini API key")
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Optional Groq API key")
    LLM_MODEL: str = Field(default="gemini-1.5-flash", description="Default LLM model name")

    # Semantic RAG Configuration (Level 3)
    EMBEDDING_MODEL_NAME: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Local embedding model identifier",
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="policy_knowledge_base",
        description="ChromaDB collection name",
    )
    RAG_MAX_CHUNKS: int = Field(default=5, description="Maximum chunks to retrieve")
    RAG_DISTANCE_THRESHOLD: float = Field(
        default=0.80,
        description="Maximum distance score for semantic relevance (cosine/L2 distance)",
    )

    # Level 6 Authentication and Security Configuration
    SECRET_KEY: str = Field(
        default="resolveai-super-secret-key-development-2026-secure-random",
        description="Secret key for signing HMAC-SHA256 authentication tokens",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=480,
        description="Access token expiration window in minutes (default 8 hours)",
    )
    AUTH_DEV_MODE_FALLBACK: bool = Field(
        default=True,
        description="Allow unauthenticated reviewer_id fallback in development and testing mode only",
    )

    # Level 6 Approval SLA Configuration
    SLA_STANDARD_HOURS: int = Field(
        default=12,
        description="Target SLA resolution window in hours for standard Tier 2 supervisor approvals",
    )
    SLA_HIGH_VALUE_HOURS: int = Field(
        default=4,
        description="Target SLA resolution window in hours for high-value senior supervisor approvals",
    )

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def attach_frontend_url_to_cors(self) -> "Settings":
        if self.FRONTEND_URL:
            clean_url = self.FRONTEND_URL.strip().rstrip("/")
            if isinstance(self.CORS_ORIGINS, list):
                if clean_url not in self.CORS_ORIGINS:
                    self.CORS_ORIGINS.append(clean_url)
            elif isinstance(self.CORS_ORIGINS, str):
                self.CORS_ORIGINS = [self.CORS_ORIGINS, clean_url]
        return self

    @property
    def project_root(self) -> Path:
        """Returns the project root directory."""
        return PROJECT_ROOT

    @property
    def is_production(self) -> bool:
        """Indicates whether the application is running in production mode."""
        return self.APP_ENV.strip().lower() == "production"

    @property
    def allow_dev_auth_fallback(self) -> bool:
        """
        Determines if unauthenticated reviewer fallback is allowed.
        In production, development fallback is strictly disabled regardless of setting.
        """
        if self.is_production:
            return False
        return self.AUTH_DEV_MODE_FALLBACK

    @property
    def POLICIES_DIR(self) -> Path:
        """Returns the canonical policies directory."""
        return PROJECT_ROOT / "data" / "policies"

    @property
    def VECTOR_STORE_DIR(self) -> Path:
        """Returns the canonical vector store directory."""
        return PROJECT_ROOT / "data" / "vector_store"

    @property
    def resolved_database_url(self) -> str:
        """
        Resolves SQLite database URLs to an absolute file path anchored at project_root.
        Prevents multiple databases from being created when the application is launched
        from different working directories.
        """
        db_url = self.DATABASE_URL
        if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
            # Format: sqlite:///relative_path
            raw_path = db_url[len("sqlite:///"):]
            if raw_path == ":memory:":
                return db_url
            target_path = Path(raw_path)
            if not target_path.is_absolute():
                abs_path = (self.project_root / target_path).resolve()
                # Ensure parent directory exists
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                # SQLite URL with absolute path (forward slashes for URI consistency)
                return f"sqlite:///{abs_path.as_posix()}"
        return db_url

    @property
    def resolved_checkpoint_db_path(self) -> Path:
        """
        Resolves the dedicated SQLite checkpoint database path anchored at project_root.
        Ensures the parent directory exists.
        """
        raw = self.CHECKPOINT_DB_PATH
        if raw == ":memory:":
            return Path(":memory:")
        target_path = Path(raw)
        if not target_path.is_absolute():
            abs_path = (self.project_root / target_path).resolve()
        else:
            abs_path = target_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return abs_path


# Global settings instance
settings = Settings()
