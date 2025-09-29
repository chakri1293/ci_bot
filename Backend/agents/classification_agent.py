# agents/classification_agent.py
from typing import Dict
import json
from datetime import datetime

class ClassificationAgent:
    """
    Handles:
        - Accepting user query
        - Classifying mode (competitor, news, blended, greeting, irrelevant)
        - Normalizing/Reconstructing the query itself
        - Greeting detection handled via LLM responses (LLM decides greeting text)
    """
    def __init__(self, llm_client,mongo_db):
        self.llm = llm_client
        self.collection = mongo_db["query_logs"]

    def classify_query(self, user_query: str) -> Dict:
        """
        Returns a dict with keys:
         - 'query' (normalized_query / response text)
         - 'mode' (competitor|news|blended|greeting|irrelevant)
         - 'final' (bool) -> True when greeting or irrelevant (should short-circuit the pipeline)
        """
        system_prompt = (
            "You are an expert Competitive Intelligence and Market Analyst.\n"
            "For any user input, do the following:\n"
            "1) Classify the input into exactly one of: competitor, news, blended, greeting, irrelevant.\n"
            "   - competitor: questions asking about competitors or competitor activity\n"
            "   - news: requests for recent industry news, events, or updates\n"
            "   - blended: contains both competitor and news aspects\n"
            "   - greeting: casual greeting / polite opening where the user is not requesting CI or news\n"
            "   - irrelevant: unrelated to competitive intelligence or industry news\n"
            "2) Rewrite or normalize the query in a clear professional way when the mode is competitor/news/blended.\n"
            "3) If mode is greeting, produce a friendly professional greeting reply as the normalized_query (introduce yourself and offer help).\n"
            "4) If mode is irrelevant, produce a short polite reply as the normalized_query: e.g. 'Only competitive intelligence & industry news supported.'\n"
            "Important: do NOT hardcode greeting keywords in your behavior — decide based on the user's text.\n\n"
            "Return ONLY valid JSON in this exact format (no extra text):\n"
            '{ "mode": "competitor|news|blended|greeting|irrelevant", "normalized_query": "..." }\n'
        )

        default_mode = "irrelevant"
        normalized = "Only competitive intelligence & industry news supported."
        mode = default_mode
        final = False

        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
            )
            raw_content = response.get("content", "").strip()

            # Try to parse direct JSON returned by the LLM
            parsed = None
            if raw_content.startswith("{"):
                try:
                    parsed = json.loads(raw_content)
                except Exception:
                    parsed = None

            # If can't parse JSON directly, try to find a JSON substring
            if parsed is None:
                try:
                    start = raw_content.find("{")
                    end = raw_content.rfind("}") + 1
                    if start != -1 and end != -1 and end > start:
                        parsed = json.loads(raw_content[start:end])
                except Exception:
                    parsed = None

            if parsed:
                mode = parsed.get("mode", default_mode).lower()
                normalized = parsed.get("normalized_query", normalized)
            else:
                # If LLM didn't return JSON, fall back to conservative behavior:
                mode = default_mode
                normalized = "Only competitive intelligence & industry news supported."

            # Normalize mode and determine if final
            if mode not in ["competitor", "news", "blended", "greeting", "irrelevant"]:
                mode = "irrelevant"

            if mode in ["greeting", "irrelevant"]:
                final = True

            # If LLM returned an empty normalized query for a final mode, use default message
            if final and not normalized.strip():
                if mode == "greeting":
                    normalized = "Hello! I am your Competitive Intelligence Assistant. How can I help you today?"
                else:
                    normalized = "Only competitive intelligence & industry news supported."
            
            # Log to Mongo
            self.collection.insert_one({
                "original_query": user_query,
                "mode": mode,
                "normalized_query": normalized,
                "timestamp": datetime.utcnow()
            })

        except Exception as e:
            # On error default to irrelevant final response
            # print(f"LLM error in ClassificationAgent: {e}")
            mode = "irrelevant"
            normalized = "Only competitive intelligence & industry news supported."
            final = True

        # Return a consistent dict
        return {"query": normalized, "mode": mode, "final": final}
