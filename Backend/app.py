import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph_orchestrator import MultiAgentPipeline
import openai
import uvicorn
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()


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
            temperature=0.3,
            max_tokens=1000,
        )
        return {"content": response.choices[0].message.content.strip()}


# FastAPI app
app = FastAPI(title="Multi-Agent Competitive Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_client = LLMClient()
pipeline = MultiAgentPipeline(llm_client)


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
