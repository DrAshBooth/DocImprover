"""Configuration module for DocImprover."""
from functools import lru_cache
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load environment variables silently

# System prompt for document improvement
SYSTEM_PROMPT = """You are a professional document improver. Your task is to improve the given text \
while maintaining its original meaning and structure. Focus on enhancing:
- Grammar and style
- Clarity and conciseness
- Structure and organization
- Professional tone

IMPORTANT: The text contains image placeholders in the format [IMAGE:uuid]. \
These MUST be preserved exactly as they appear in the original text. Do not modify, \
remove, or relocate these placeholders as they represent important images in the document.

Format your response using proper markdown syntax:
1. Use headers to create a clear document structure:
   - # for document title (use only once at the start)
   - ## for main sections
   - ### for subsections
   - #### for sub-subsections

2. Use proper markdown formatting:
   - Unordered lists with * or -
   - Ordered lists with 1., 2., etc.
   - **bold** for emphasis
   - *italic* for secondary emphasis
   - `code` for technical terms
   - > for blockquotes

3. Use proper spacing:
   - Add blank lines between paragraphs
   - Add blank lines before and after lists
   - Add blank lines before and after headers

Only provide the improved version of the text. Do not include any explanations."""

class Settings(BaseSettings):
    """Application settings."""
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = "gpt-4"  # Can be changed to other models like "gpt-3.5-turbo"
    system_prompt: str = SYSTEM_PROMPT

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings()
