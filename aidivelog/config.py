"""
Configuration settings for the unified dive assistant system.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env file in the project root (parent of aidivelog directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return api_key


# Pinecone API key function removed - using SQLite instead

