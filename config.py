import os
from typing import Optional

class Settings:
    """Application configuration settings."""
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:root@localhost:5432/trip_planner"
    )
    
    # Ollama/LLM settings
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security settings (for future use)
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    
    # Feature flags
    ENABLE_AI_RECOMMENDATIONS: bool = os.getenv("ENABLE_AI_RECOMMENDATIONS", "true").lower() == "true"

# Global settings instance
settings = Settings()