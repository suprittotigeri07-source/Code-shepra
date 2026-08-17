"""Configuration loader for Code Sherpa backend."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://sherpa:sherpa_secret_2024@localhost:5433/code_sherpa")
    DATABASE_URL_SYNC: str = os.getenv("DATABASE_URL_SYNC", "postgresql://sherpa:sherpa_secret_2024@localhost:5433/code_sherpa")
    
    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_CHAT_MODEL: str = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5-coder:7b")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
    
    # App
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    
    # Retrieval
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "10"))
    MAX_AGENT_ITERATIONS: int = int(os.getenv("MAX_AGENT_ITERATIONS", "10"))


settings = Settings()
