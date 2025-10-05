# agents/classification_agent.py
from typing import Dict
from collections import deque
from datetime import datetime
import re
import json

class ClassificationAgent:
    """
    Handles:
        - Accepting user query
        - Classifying mode (competitor, news, blended, greeting, irrelevant)
        - Normalizing/Reconstructing the query itself
        - Greeting detection via simple rules
        - Maintains last N interactions for context
    """
    SIMPLE_GREETINGS = re.compile(r"^(hi|hello|hey|good morning|good afternoon|good evening|greetings)\b", re.I)

    def __init__(self, llm_client, mongo_db, history_size: int = 4):
        self.llm = llm_client
        self.collection = mongo_db["query_logs"]
        self.query_history = deque(maxlen=history_size)

    def classify_query(self, user_query: str) -> Dict:
        user_query_clean = user_query.strip()

        # --- Shortcut for simple greetings ---
        if self.SIMPLE_GREETINGS.match(user_query_clean):
            normalized = "Hello! I am your Competitive Intelligence Assistant. How can I help you today?"
            mode = "greeting"
            final = True
            self._log_query(user_query, mode, normalized)
            self._update_history(user_query, normalized)
            return {"assistant_message": normalized, "mode": mode, "final": final}

        # --- Default fallback ---
        default_mode = "irrelevant"
        normalized = "Only competitive intelligence & industry news supported."
        mode = default_mode
        final = False

        system_prompt = (
            "You are an expert Competitive Intelligence and Market Analyst.\n"
            "Classify input into one of: competitor, news, blended, greeting, irrelevant.\n"
            "Rewrite query professionally for competitor/news/blended.\n"
            "If greeting, produce friendly professional greeting.\n"
            "If irrelevant, produce short polite response.\n"
            "Consider last interactions.\n"
            "If the input is not related to industry, competitors, or market/industry news, treat it strictly as 'irrelevant' without assuming external context or fabricating knowledge.\n"
            "Return ONLY valid JSON in this format:\n"
            '{ "mode": "competitor|news|blended|greeting|irrelevant", "normalized_query": "..." }'
        )

        try:
            # Prepare context
            history_messages = []
            for h in self.query_history:
                history_messages.extend([
                    {"role": "user", "content": h["original_query"]},
                    {"role": "assistant", "content": h["assistant_message"]}
                ])
            history_messages.append({"role": "user", "content": user_query})

            # LLM classification call
            response = self.llm.chat(messages=[{"role": "system", "content": system_prompt}] + history_messages)
            raw_content = response.get("content", "").strip()

            # Parse JSON safely
            parsed = self._safe_json_parse(raw_content)

            if parsed:
                mode = parsed.get("mode", default_mode).lower()
                normalized = parsed.get("normalized_query", normalized)
            else:
                mode = default_mode
                normalized = "Only competitive intelligence & industry news supported."

            if mode not in ["competitor", "news", "blended", "greeting", "irrelevant"]:
                mode = "irrelevant"

            if mode in ["greeting", "irrelevant"]:
                final = True
                if not normalized.strip():
                    normalized = (
                        "Hello! I am your Competitive Intelligence Assistant. How can I help you today?"
                        if mode == "greeting" else
                        "Only competitive intelligence & industry news supported."
                    )

        except Exception:
            mode = "irrelevant"
            normalized = "Only competitive intelligence & industry news supported."
            final = True

        # Log and update history
        self._log_query(user_query, mode, normalized)
        self._update_history(user_query, normalized)

        return {"assistant_message": normalized, "mode": mode, "final": final}

    # ---------------- Helper Methods ----------------
    def _safe_json_parse(self, text: str) -> Dict:
        """Extract valid JSON from LLM response"""
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try extracting first {...} block
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end])
                except Exception:
                    return None
        return None

    def _log_query(self, user_query: str, mode: str, normalized: str):
        try:
            self.collection.insert_one({
                "original_query": user_query,
                "mode": mode,
                "normalized_query": normalized,
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            print("Mongo logging failed in ClassificationAgent:", e)

    def _update_history(self, user_query: str, normalized: str):
        self.query_history.append({
            "original_query": user_query,
            "assistant_message": normalized
        })
