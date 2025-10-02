from typing import List, Dict
from tavily import TavilyClient

class TavilySearchAgent:
    """
    Search agent using a shared Tavily client.
    """

    def __init__(self, tavily_client: TavilyClient):
        """
        tavily_client: an instance of TavilyClient passed from outside
        """
        self.client = tavily_client

    def _run_search(self, query: str, topic: str) -> List[Dict]:
        """
        Helper to run search for a given topic and normalize results.
        Only returns results with score > 0.5
        """
        response = self.client.search(
            query=query,
            topic=topic,
            search_depth="basic",
            include_answer=False,
            include_raw_content=False,
            max_results=5,
            auto_parameters=False  # Explicitly set to False
        )
        results = response.get("results", [])
        return [
            {**r, "score": r.get("score", 0), "topic": topic}
            for r in results if r.get("score", 0) > 0.5
        ]

    def search(self, query: str, mode: str) -> List[Dict]:
        """
        mode: "news", "competitor", "blended"
        """
        if mode == "news":
            return self._run_search(query, "news")
        elif mode == "competitor":
            return self._run_search(query, "general")
        elif mode == "blended":
            general_results = self._run_search(query, "general")
            news_results = self._run_search(query, "news")
            return general_results + news_results
        else:
            raise ValueError(f"Invalid search mode: {mode}")
