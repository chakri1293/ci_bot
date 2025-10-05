import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph_orchestrator import MultiAgentPipeline
import openai
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from tavily import TavilyClient
from config import settings  # ✅ Centralized config


# ---- Initialize OpenAI Client ----
class LLMClient:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

    def chat(self, messages):
        response = openai.ChatCompletion.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT
        )
        return {"content": response.choices[0].message.content.strip()}


# ---- Initialize Tavily Client ----
class TavilyAPIClient:
    def __init__(self):
        if not settings.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY not set in environment")
        self.client = TavilyClient(api_key=settings.TAVILY_API_KEY)


# ---- MongoDB Client Setup ----
mongo_client = MongoClient(settings.MONGO_URI)
mongo_db = mongo_client[settings.MONGODB_NAME]


# ---- FastAPI Setup ----
app = FastAPI(title="Multi-Agent Competitive Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can be restricted later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_client = LLMClient()
tavily_client = TavilyAPIClient()

# Initialize Multi-Agent Pipeline
pipeline = MultiAgentPipeline(llm_client, tavily_client.client, mongo_db)


# ---- API Models & Routes ----
class QueryRequest(BaseModel):
    query: str


@app.get("/")
async def root():
    return {"message": "Multi-Agent Competitive Intelligence API is running"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/query")
async def handle_query(request: QueryRequest):
    result = pipeline.run_pipeline(request.query)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# if __name__ == "__main__":
#     uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
