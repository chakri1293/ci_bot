# agents/formatter_agent.py
from typing import Dict
from datetime import datetime

class FormatterAgent:
    """
    Formats aggregated results for final user response in a UI-friendly way.
    Supports text, bullets, numbered lists, paragraphs, and images.
    """

    MAX_BULLETS = 10  # max bullets to show (optional, can be used in formatting)

    def __init__(self, llm_client, mongo_db):
        """
        llm_client: a client with a chat() method that accepts messages
        [{"role": "user", "content": "..."}] and returns a dict with 'content'.
        """
        self.llm = llm_client
        self.collection = mongo_db["response_logs"]

    def format(self, query: str, agg_result: Dict) -> Dict:
        """
        Formats aggregated result into a structured, user-friendly response.
        """
        if not agg_result or "summary" not in agg_result:
            return {"summary": "No relevant information found.", "topics": {}, "raw_extractions": [], "content_blocks": []}

        raw_summary = agg_result.get("summary", "").strip()
        topics = agg_result.get("topics", {})
        raw_extractions = agg_result.get("raw_extractions", [])

        # ---------- Build structured content blocks ----------
        content_blocks = []

        # Add main summary
        if raw_summary:
            content_blocks.append({"type": "paragraph", "text": raw_summary})

        # Add topic sections
        for topic, text in topics.items():
            if text and text != "NO RELEVANT INFO":
                content_blocks.append({"type": "topic", "title": topic, "text": text})

        # Add images from raw extractions
        for raw in raw_extractions:
            if raw.get("type") == "image" and raw.get("url"):
                content_blocks.append({"type": "image", "content": raw["url"], "meta": raw.get("meta", {})})

        # ---------- Optional: LLM formatting to enhance readability ----------
        if content_blocks:
            try:
                prompt = (
                    "You are an expert assistant. Take the following content blocks and produce "
                    "a visually clean, concise, user-friendly response. Preserve paragraphs, bullets, "
                    "and topic sections. Do not add extra knowledge.\n\n"
                    f"{content_blocks}"
                )
                llm_response = self.llm.chat([{"role": "user", "content": prompt}])
                llm_text = llm_response.get("content", "").strip()
                if llm_text:
                    # Replace blocks with LLM-enhanced single paragraph
                    content_blocks = [{"type": "paragraph", "text": llm_text}]
            except Exception as e:
                print("LLM formatting step failed:", e)

        # ---------- Log to MongoDB ----------
        try:
            self.collection.insert_one({
                "normalized_query": query,
                "response": {
                    "summary": raw_summary,
                    "topics": topics,
                    "raw_extractions": raw_extractions,
                    "content_blocks": content_blocks
                },
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            print("Mongo logging failed:", e)

        return {
            "summary": raw_summary,
            "topics": topics,
            "raw_extractions": raw_extractions,
            "content_blocks": content_blocks
        }
