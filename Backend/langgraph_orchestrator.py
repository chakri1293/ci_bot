# multi_agent_pipeline.py
from langgraph.graph import StateGraph
from typing import Dict, Literal

class MultiAgentPipeline:
    def __init__(self, llm_client, tavily_client, mongo_db):
        self.llm_client = llm_client
        self.tavily_client = tavily_client  # pass shared TavilyClient
        self.mongo_db = mongo_db

        # Import agents
        from agents.classification_agent import ClassificationAgent
        from agents.tavily_search_agent import TavilySearchAgent
        from agents.tavily_extract_agent import TavilyExtractAgent
        from agents.tavily_crawl_agent import TavilyCrawlAgent
        from agents.smart_aggregator_agent import SmartAggregatorAgent
        from agents.formatter_agent import FormatterAgent

        # Initialize agents
        self.input_agent = ClassificationAgent(llm_client,self.mongo_db)
        self.search_agent = TavilySearchAgent(self.tavily_client)
        self.extract_agent = TavilyExtractAgent(self.tavily_client)
        self.crawl_agent = TavilyCrawlAgent(self.tavily_client)
        self.aggregate_agent = SmartAggregatorAgent(llm_client)
        self.formatter_agent = FormatterAgent(llm_client,self.mongo_db)

        # Create graph
        self.graph = StateGraph(dict)

        # Add nodes with safe wrapper
        self.graph.add_node("ClassificationAgent", self._safe(self._classify))
        self.graph.add_node("TavilySearchAgent", self._safe(self._search_node))
        self.graph.add_node("TavilyExtractAgent", self._safe(self._extract))
        self.graph.add_node("TavilyCrawlAgent", self._safe(self._crawl))
        self.graph.add_node("SmartAggregatorAgent", self._safe(self._aggregate))
        self.graph.add_node("FormatterAgent", self._safe(self._format))

        # Preserve normal edges
        self.graph.add_edge("TavilyExtractAgent", "SmartAggregatorAgent")
        self.graph.add_edge("TavilyCrawlAgent", "SmartAggregatorAgent")
        self.graph.add_edge("SmartAggregatorAgent", "FormatterAgent")

        # Conditional routing from ClassificationAgent
        def _route_from_classify(state: Dict) -> Literal["FormatterAgent", "TavilySearchAgent"]:
            classified = state.get("classified", {})
            if classified.get("final"):
                return "FormatterAgent"
            return "TavilySearchAgent"

        self.graph.add_conditional_edges(
            "ClassificationAgent",
            self._safe(_route_from_classify),
            {
                "FormatterAgent": "FormatterAgent",
                "TavilySearchAgent": "TavilySearchAgent"
            }
        )

        # Conditional routing from TavilySearchAgent
        def _route_after_search(state: Dict) -> str:
            if state.get("high_score_urls"):
                return "TavilyExtractAgent"
            if state.get("mid_score_urls"):
                return "TavilyCrawlAgent"
            return "SmartAggregatorAgent"

        self.graph.add_conditional_edges(
            "TavilySearchAgent",
            self._safe(_route_after_search),
            {
                "TavilyExtractAgent": "TavilyExtractAgent",
                "TavilyCrawlAgent": "TavilyCrawlAgent",
                "SmartAggregatorAgent": "SmartAggregatorAgent"
            }
        )

        # Set entry and finish points
        self.graph.set_entry_point("ClassificationAgent")
        self.graph.set_finish_point("FormatterAgent")

        # Compile graph
        self.app = self.graph.compile()

    # ---------- Safe wrapper ----------
    def _safe(self, fn):
        def wrapped(state: Dict):
            try:
                return fn(state)
            except Exception as e:
                state["error"] = 'An error occurred while processing your request.'
                # print(f"Pipeline error in {fn.__name__}: {e}")
                return state
        return wrapped

    # ---------- Node implementations ----------
    def _classify(self, state: Dict) -> Dict:
        query = state.get("query", "")
        classified = self.input_agent.classify_query(query)
        # print("Classification done:", classified)
        state["classified"] = classified

        # If greeting/irrelevant, put the response for final output
        if classified.get("final"):
            state["final_response"] = classified.get("query", "")
        return state

    def _search_node(self, state: Dict) -> Dict:
        if state.get("error"):
            return state
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
        if state.get("error"):
            return state
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
        if state.get("error"):
            return state
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
        if state.get("error"):
            state["aggregated"] = []
            return state
        docs = state.get("docs", [])
        url_with_topics = state.get("url_with_topics", [])
        query = state.get("classified", {}).get("query", "")
        if docs:
            aggregated = self.aggregate_agent.process_documents(query, docs, url_with_topics)
            state["aggregated"] = aggregated
        else:
            state["aggregated"] = []
        print("Aggregate completed")
        return state

    # ---------- _format node ----------
    def _format(self, state: Dict) -> Dict:
        if state.get("error"):
            return {
                "output": {
                    "type": "text",
                    "content": "An error occurred while processing your request.",
                    "meta": {}
                }
            }

        # Handle final_response from classification (greeting/irrelevant)
        final_response = state.get("final_response")
        if final_response is not None:
            return {
                "output": {
                    "type": "text",
                    "content": final_response,
                    "meta": {"short_circuit": True}
                }
            }

        # Normal aggregation formatting
        aggregated = state.get("aggregated", {})
        if not aggregated:
            return {
                "output": {
                    "type": "text",
                    "content": "Didn't find any relevant information.",
                    "meta": {}
                }
            }
        
        query = state.get("classified", {}).get("query", "")
        formatted = self.formatter_agent.format(query,aggregated)
        content_blocks = formatted.get("content_blocks", [])
        if not content_blocks:
            content_blocks = [{"type": "paragraph", "text": formatted.get("summary", "Didn't find any relevant information.")}]

        return {
            "output": {
                "type": "mixed" if len(content_blocks) > 1 else "text",
                "content": content_blocks if len(content_blocks) > 1 else content_blocks[0]["text"],
                "meta": {"urls": [d.get("url") for d in state.get("url_with_topics", [])]}
            }
        }

    # ---------- Public API ----------
    def run_pipeline(self, query: str):
        inputs = {"query": query}
        try:
            result = self.app.invoke(inputs)
        except Exception as e:
            # print(f"Invocation error: {e}")
            return {"status": "error", "message": "An error occurred while processing your request."}

        if "output" not in result:
            return {"status": "error", "message": result.get("error", "An error occurred while processing your request.")}
        return {"status": "success", "data": result["output"]}
