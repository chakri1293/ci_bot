import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Load environment variables for API keys and app config
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
    CRAWL_DEPTH = int(os.getenv("CRAWL_DEPTH", "1"))
    CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "5"))
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGODB_NAME = os.getenv("MONGODB_NAME", "multiagentdb")
    THREADPOOL_WORKERS = int(os.getenv("THREADPOOL_WORKERS", "5"))

settings = Settings()
