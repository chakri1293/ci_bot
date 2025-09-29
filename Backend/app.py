import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph_orchestrator import MultiAgentPipeline
import openai
import uvicorn
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from tavily import TavilyClient  # import TavilyClient
from pymongo import MongoClient


# Load environment variables
load_dotenv()

# ---- MongoDB Client Setup ----
MONGO_URI = os.getenv("MONGO_URI")  # Add to .env: MONGO_URI="mongodb+srv://..."
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["multi_agent_ci"]

# Real LLM client wrapper using OpenAI API key from env
class LLMClient:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

    def chat(self, messages):
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.0,
            max_tokens=800,
            timeout=6
        )
        return {"content": response.choices[0].message.content.strip()}


# Tavily client wrapper
class TavilyAPIClient:
    def __init__(self):
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY not set in environment")
        self.client = TavilyClient(api_key=tavily_api_key)


# FastAPI app
app = FastAPI(title="Multi-Agent Competitive Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("APP_URL")],  # React dev server origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
llm_client = LLMClient()
tavily_client = TavilyAPIClient()

# Pass llm_client and tavily_client.client to your pipeline if needed
pipeline = MultiAgentPipeline(llm_client, tavily_client.client,mongo_db)  # Adjust constructor


class QueryRequest(BaseModel):
    query: str


@app.post("/query")
async def handle_query(request: QueryRequest):
    result = pipeline.run_pipeline(request.query)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
