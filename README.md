# Multi-Agent Competitive Intelligence API

This project is a FastAPI-based microservice providing multi-agent competitive intelligence functionality with integrations for Tavily, OpenAI, MongoDB, and LangGraph orchestration.

https://www.loom.com/share/05ab568789104f32a6fe50d21d27b717?sid=3c41d6a0-3ce1-4ffe-9a85-a99da02db56f

## Features
- Modular agent design (extract, crawl, search, format, classify, aggregate)
- LangGraph orchestration for multi-agent workflows
- Tavily and OpenAI integrations
- MongoDB for persistent data storage

## Process Flow

  The system is a **multi-agent architecture** orchestrated via `LangGraphOrchestrator`.

  ### Agents & Responsibilities

  #### 1. Classification Agent
  - Classifies the input query into:
    - **Greeting** → routed to `Formatter Agent`
    - **Competitive / Industry Related** → assigns topics → routed to `Search Agent`
    - **Irrelevant** → routed to `Formatter Agent`

  #### 2. Search Agent (`tavily_search`)
  - Searches relevant URLs based on assigned topics
  - Orchestrator decides whether to invoke `Extract Agent` or `Crawl Agent`

  #### 3. Extract / Crawl Agents (`tavily_extract` / `tavily_crawl`)
  - Orchestrator decision to Extracts or crawls text content from URLs
  - Only **one agent** is invoked per query

  #### 4. Smart Aggregator Agent
  - Summarizes and condenses extracted content using **LLM**
  - Generates a concise, query-relevant summary
  - Sends output to `Formatter Agent`

  #### 5. Formatter Agent
  - Formats aggregated response for **React UI display**
  - Handles fallback responses if any agent fails

  ### Error Handling
  - Any agent failure → `Formatter Agent` ensures a response is returned

## Process Flow Diagram

    User Input
        ↓
    LangGraph Orchestrator
        ↓
    Classification Agent
        ├─ Greeting/Irrelevant ──→ Formatter Agent
        └─ Competitive/Industry ──→ Search Agent
                                    ↓
                              Orchestrator Decision
                        ┌────────────┴─────────────┐
                        ↓                          ↓
                Extract Agent             Crawl Agent
                        ↓                          ↓
                            Smart Aggregator Agent
                                      ↓
                          Formatter Agent (Final Output)
                              
    Error Handling: Any agent failure → Formatter Agent


## Quick Start

1. Clone the repository
2. Add a `.env` file with keys:

    TAVILY_API_KEY=your-key
    OPENAI_API_KEY=your-key
    MONGOURI=mongodb+srv://your-uri
    MONGODBNAME=your-db
    LLMMODEL=gpt-4o
    CRAWLDEPTH=1
    CRAWLMAXPAGES=5
    THREADPOOLWORKERS=5
    APPURL=http://localhost:3000

3. Build and run:

    docker-compose up --build   


## Development

- Python 3.10+
  python -m pip install --upgrade pip setuptools wheel
- Install dependencies: `pip install -r requirements.txt`
- Run locally: `uvicorn app:app --reload`

## Code Structure

- `app.py`: Main FastAPI app
- `config.py`: Environment/config loader
- Agents: `*_agent.py`
- Orchestration: `langgraph_orchestrator.py`

### ✅ Database (MongoDB Atlas - Cloud Hosted)

The application uses **MongoDB Atlas** as the primary database for storing queries, agent outputs, and metadata.  
The database is fully managed and hosted in the cloud, enabling secure and scalable storage.

- **Hosting Platform:** MongoDB Atlas (Cloud Managed Cluster)
- **Access Console:**  
  https://cloud.mongodb.com/v2/68dec78a8742d130c0f1b09b#/metrics/replicaSet/68dec83a68750907d56e7bfd/explorer
- **Connection:** Configured via `MONGO_URI` and `MONGODB_NAME` environment variables
- **Security:** IP whitelisting enabled — access granted to Elastic Beanstalk instances and developer IP ranges

> ✅ All database credentials are securely passed through environment variables (`.env` for local and `setenv` in Elastic Beanstalk).


## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/health` | Health check |
| POST   | `/query` | Run the intelligence pipeline |

## Deployment

### ✅ Live Deployment (AWS Elastic Beanstalk)

The API is deployed on AWS Elastic Beanstalk and can be accessed here:

🔗 **Health Check:**  
http://ci-news-system-env.eba-mpx8mspp.us-west-2.elasticbeanstalk.com/health

You can replace `/health` with `/query` to make application-level requests.

Example `curl`:

```bash
curl -X POST \
  http://ci-news-system-backendapi-env.eba-8fpv57cs.us-west-2.elasticbeanstalk.com/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Latest AI trends"}'

### ✅ Frontend Deployment (AWS S3)

http://ci-news-frontend-app.s3-website-us-west-2.amazonaws.com/


