"""Configuration module for DocImprover."""
from functools import lru_cache
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load environment variables silently

class Settings(BaseSettings):
    """Application settings."""
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = "gpt-4"  # Can be changed to other models like "gpt-3.5-turbo"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings()
