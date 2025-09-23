from langgraph.graph import StateGraph, END


class MultiAgentPipeline:
    def __init__(self, llm_client):
        self.llm_client = llm_client

        # Import agents
        from agents.input_agent import InputAgent
        from agents.fetch_extract_agent import FetchAndExtractAgent
        from agents.dedup_summarize_agent import DedupAndSummarizeAgent
        from agents.aggregator_agent import AggregatorAgent
        from agents.formatter_agent import FormatterAgent

        self.input_agent = InputAgent(llm_client)
        self.fetch_agent = FetchAndExtractAgent()
        self.dedup_agent = DedupAndSummarizeAgent(llm_client)
        self.aggregator_agent = AggregatorAgent(llm_client)
        self.formatter_agent = FormatterAgent(llm_client)

        # Create a state graph
        self.graph = StateGraph(dict)

        # Add nodes (each updates state)
        self.graph.add_node("InputAgent", self._input)
        self.graph.add_node("FetchExtractAgent", self._fetch)
        self.graph.add_node("DedupSummarizeAgent", self._dedup)
        self.graph.add_node("AggregatorAgent", self._aggregate)
        self.graph.add_node("FormatterAgent", self._format)

        # Define edges (flow of pipeline)
        self.graph.add_edge("InputAgent", "FetchExtractAgent")
        self.graph.add_edge("FetchExtractAgent", "DedupSummarizeAgent")
        self.graph.add_edge("DedupSummarizeAgent", "AggregatorAgent")
        self.graph.add_edge("AggregatorAgent", "FormatterAgent")

        # Entry and finish
        self.graph.set_entry_point("InputAgent")
        self.graph.set_finish_point("FormatterAgent")

        # Compile pipeline into runnable graph
        self.app = self.graph.compile()

    # Node logic wrappers
    def _input(self, state):
        query = state["query"]
        classified = self.input_agent.classify_query(query)
        return {"classified": classified}

    def _fetch(self, state):
        docs = self.fetch_agent.fetch_documents(state["classified"])
        return {"docs": docs}

    def _dedup(self, state):
        summaries = self.dedup_agent.process_documents(state["docs"])
        return {"summaries": summaries}

    def _aggregate(self, state):
        mode = state.get("mode", "general")
        aggregated = self.aggregator_agent.aggregate(state["summaries"], mode)
        return {"aggregated": aggregated}

    def _format(self, state):
        mode = state.get("mode", "general")
        output = self.formatter_agent.format(state["aggregated"],mode)
        return {"output": output}

    # Public API
    def run_pipeline(self, query: str):
        inputs = {"query": query}
        print(inputs)
        result = self.app.invoke(inputs)

        if "output" not in result:
            return {"status": "error", "message": "Failed to produce output."}
        return {"status": "success", "data": result["output"]}
