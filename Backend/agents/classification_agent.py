from typing import Dict
import os

class ClassificationAgent:
    """
    Handles:
        - Accepting user query
        - Classifying mode (competitor, news, blended, irrelevant)
        - Normalizing/Reconstructing the query itself
    """
    def __init__(self, llm_client):
        self.llm = llm_client

    def classify_query(self, user_query: str) -> Dict:
        system_prompt = (
            "You are an expert Competitive Intelligence and Market Analyst. "
            "Given a user query, do two things:\n"
            "1. Classify the query into one of: competitor, news, blended, irrelevant.\n"
            "2. Rewrite the query in a clear, structured, professional way "
            "(normalize grammar, expand context like timeframe, product, or industry if possible).\n\n"
            "Return ONLY in this format:\n"
            "{ \"mode\": \"competitor|news|blended|irrelevant\", \"normalized_query\": \"...\" }"
        )
        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
            )

            raw_content = response.get("content", "").strip()

            # Try parsing simple JSON-like response
            mode, normalized = "irrelevant", user_query
            if raw_content.startswith("{"):
                import json
                try:
                    parsed = json.loads(raw_content)
                    mode = parsed.get("mode", "irrelevant").lower()
                    normalized = parsed.get("normalized_query", user_query)
                except Exception:
                    pass

            if mode not in ["competitor", "news", "blended", "irrelevant"]:
                mode = "irrelevant"

            # overwrite user_query with normalized one
            user_query = normalized

        except Exception as e:
            print(f"LLM error: {e}")
            mode = "irrelevant"

        print(mode, user_query)
        return {"query": user_query, "mode": mode}


# Example usage
# if __name__ == "__main__":
#     class DummyLLM:
#         def chat(self, messages):
#             return {
#                 "content": '{ "mode": "news", "normalized_query": "Summarize the latest news about the Electric Vehicle industry in September 2025, focusing on competitor activities and product launches." }'
#             }

#     agent = InputAgent(DummyLLM())
#     test_query = "EV news this month"
#     print(agent.classify_query(test_query))
