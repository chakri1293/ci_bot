# multi_agent_pipeline.py
from langgraph.graph import StateGraph
from typing import Dict, List, Literal

class MultiAgentPipeline:
    def __init__(self, llm_client, tavily_client):
        self.llm_client = llm_client
        self.tavily_client = tavily_client  # pass shared TavilyClient

        # Import agents
        from agents.classification_agent import ClassificationAgent
        from agents.tavily_search_agent import TavilySearchAgent
        from agents.tavily_extract_agent import TavilyExtractAgent
        from agents.tavily_crawl_agent import TavilyCrawlAgent
        from agents.smart_aggregator_agent import SmartAggregatorAgent
        from agents.formatter_agent import FormatterAgent

        # Initialize agents
        self.input_agent = ClassificationAgent(llm_client)
        self.search_agent = TavilySearchAgent(self.tavily_client)
        self.extract_agent = TavilyExtractAgent(self.tavily_client)
        self.crawl_agent = TavilyCrawlAgent(self.tavily_client)
        self.aggregate_agent = SmartAggregatorAgent(llm_client)
        self.formatter_agent = FormatterAgent(llm_client)

        # Create graph
        self.graph = StateGraph(dict)

        # Add nodes
        self.graph.add_node("ClassificationAgent", self._classify)
        self.graph.add_node("TavilySearchAgent", self._search_node)
        self.graph.add_node("TavilyExtractAgent", self._extract)
        self.graph.add_node("TavilyCrawlAgent", self._crawl)
        self.graph.add_node("SmartAggregatorAgent", self._aggregate)
        self.graph.add_node("FormatterAgent", self._format)

        # Add normal edges
        self.graph.add_edge("ClassificationAgent", "TavilySearchAgent")
        self.graph.add_edge("TavilyExtractAgent", "SmartAggregatorAgent")
        self.graph.add_edge("TavilyCrawlAgent", "SmartAggregatorAgent")
        self.graph.add_edge("SmartAggregatorAgent", "FormatterAgent")

        # Conditional edges from search
        self.graph.add_conditional_edges(
            "TavilySearchAgent",
            self._route_based_on_urls,
            {
                "TavilyExtractAgent": "TavilyExtractAgent",
                "TavilyCrawlAgent": "TavilyCrawlAgent",
                "FormatterAgent": "FormatterAgent"
            }
        )

        # Set entry and finish points
        self.graph.set_entry_point("ClassificationAgent")
        self.graph.set_finish_point("FormatterAgent")

        # Compile graph
        self.app = self.graph.compile()

    # ---------- Routing function for conditional edges ----------
    def _route_based_on_urls(self, state: Dict) -> Literal["TavilyExtractAgent", "TavilyCrawlAgent", "FormatterAgent"]:
        if state.get("high_score_urls"):
            return "TavilyExtractAgent"
        elif state.get("mid_score_urls"):
            return "TavilyCrawlAgent"
        else:
            return "FormatterAgent"

    # ---------- Node implementations ----------
    def _classify(self, state: Dict) -> Dict:
        query = state.get("query", "")
        classified = self.input_agent.classify_query(query)
        print("Classification done:", classified)
        state["classified"] = classified
        return state

    def _search_node(self, state: Dict) -> Dict:
        classified = state.get("classified", {})
        query = classified.get("query", "")
        mode = classified.get("mode", "competitor")

        results = self.search_agent.search(query, mode)
        state["search_results"] = results
        print("Search done. Results count:", len(results))

        high_score_urls = [{"url": r["url"], "topic": r.get("topic", "general")} for r in results if r.get("score", 0) > 0.7]
        mid_score_urls = [{"url": r["url"], "topic": r.get("topic", "general")} for r in results if 0.5 <= r.get("score", 0) <= 0.7]

        state["high_score_urls"] = high_score_urls if high_score_urls else None
        state["mid_score_urls"] = mid_score_urls if mid_score_urls else None

        return state

    def _extract(self, state: Dict) -> Dict:
        urls = state.get("high_score_urls", [])
        if urls:
            docs = list(self.extract_agent.extract(urls))
            print("Extracted docs count:", len(docs))
            state["docs"] = docs
            state["url_with_topics"] = urls
        else:
            state["docs"] = []
        return state

    def _crawl(self, state: Dict) -> Dict:
        urls = state.get("mid_score_urls", [])
        if urls:
            docs = list(self.crawl_agent.crawl(urls))
            print("Crawled docs count:", len(docs))
            state["docs"] = docs
            state["url_with_topics"] = urls
        else:
            state["docs"] = []
        return state

    def _aggregate(self, state: Dict) -> Dict:
        docs = state.get("docs", [])
        url_with_topics = state.get("url_with_topics", [])
        query = state.get("classified", {}).get("query", "")
        if docs:
            aggregated = self.aggregate_agent.process_documents(query, docs, url_with_topics)
            # print("Aggregation done", aggregated)
            state["aggregated"] = aggregated
        else:
            state["aggregated"] = []
        return state

    def _format(self, state: Dict) -> Dict:
        aggregated = state.get("aggregated", [])
        if not aggregated:
            output = "Didn't find any relevant information."
        else:
            output = self.formatter_agent.format(aggregated)
        return {"output": output}

    # ---------- Public API ----------
    def run_pipeline(self, query: str):
        inputs = {"query": query}
        try:
            result = self.app.invoke(inputs)
        except Exception as e:
            print("LangGraph invoke failed:", e)
            return {"status": "error", "message": str(e)}

        if "output" not in result:
            return {"status": "error", "message": "Failed to produce output."}
        return {"status": "success", "data": result["output"]}
