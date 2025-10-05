import os
from dotenv import load_dotenv

# Load environment variables from .env if present (Elastic Beanstalk setenv works too)
load_dotenv()

class Settings:
    """Centralized application settings loaded from environment variables."""

    # API keys
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")

    # LLM settings
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", 0.0))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", 400))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", 5))

    # Crawling settings
    CRAWL_DEPTH: int = int(os.getenv("CRAWL_DEPTH", 1))
    CRAWL_MAX_PAGES: int = int(os.getenv("CRAWL_MAX_PAGES", 5))
    THREADPOOL_WORKERS: int = int(os.getenv("THREADPOOL_WORKERS", 5))

    # MongoDB settings
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGODB_NAME: str = os.getenv("MONGODB_NAME", "multiagentdb")


settings = Settings()
