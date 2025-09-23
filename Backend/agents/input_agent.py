from typing import Dict
import os

class InputAgent:
    """
    Handles:
        - Accepting user query
        - Classifying mode (competitor, news, blended, irrelevant)
        - Extracting filters (if any)
    """
    def __init__(self, llm_client):
        self.llm = llm_client

    def classify_query(self, user_query: str) -> Dict:
        system_prompt = (
            "You are an expert Competitive Intelligence and Market Analyst. "
            "Given a user query, determine the type of information requested - "
            "Options: "
            "1. competitor - for competitor announcements, products, launches; "
            "2. news - for industry news or market trends; "
            "3. blended - for both competitor and news context; "
            "4. irrelevant - if not related to CI/news. "
            "Respond ONLY with: competitor, news, blended, or irrelevant."
        )
        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
            )
            mode = response.get("content", "").strip().lower()
            if mode not in ["competitor", "news", "blended", "irrelevant"]:
                mode = "irrelevant"
        except Exception as e:
            print(f"LLM error: {e}")
            mode = "irrelevant"
        print(mode)
        return {"query": user_query, "mode": mode}

# # Sample run for debugging/test
# if __name__ == "__main__":
#     class DummyLLM:  # Replace for actual OpenAI/Tavily wrapper
#         def chat(self, messages): return {"content": "news"}
#     agent = InputAgent(DummyLLM())
#     test_query = "Summarize latest EV industry news"
#     print(agent.classify_query(test_query))
