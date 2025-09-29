# agents/formatter_agent.py
from typing import Dict
from datetime import datetime

class FormatterAgent:
    """
    Formats aggregated results for final user response in a UI-friendly way.
    Supports text, bullets, numbered lists, paragraphs, and images.
    """

    MAX_SUMMARY_CHARS = 2000  # truncate summary to avoid overly long text
    MAX_BULLETS = 10  # max bullets to show

    def __init__(self, llm_client,mongo_db):
        """
        llm_client: a client with a chat() method that accepts messages
        [{"role": "user", "content": "..."}] and returns a dict with 'content'.
        """
        self.llm = llm_client
        self.collection = mongo_db["response_logs"]

    def format(self, query, agg_result: Dict) -> Dict:
        """
        Formats aggregated result into a rich, structured response.
        agg_result may contain:
        - summary: raw combined summary text
        - topics: dict of topic-wise summaries
        - raw_extractions: list of extracted content per document
        """
        try:
            if not agg_result or "summary" not in agg_result:
                return {"summary": "No relevant information found.", "topics": {}, "raw_extractions": [], "content_blocks": []}

            raw_summary = agg_result.get("summary", "").strip()
            topics = agg_result.get("topics", {})
            raw_extractions = agg_result.get("raw_extractions", [])

            # ---------- Build structured content blocks ----------
            content_blocks = []
            if raw_summary:
                content_blocks.append({"type": "paragraph", "text": raw_summary})

            # Topics
            for topic, text in topics.items():
                if text and text != "NO RELEVANT INFO":
                    content_blocks.append({"type": "topic", "title": topic, "text": text})

            # Images in raw extractions
            for raw in raw_extractions:
                if raw.get("type") == "image" and raw.get("url"):
                    content_blocks.append({"type": "image", "content": raw["url"], "meta": raw.get("meta", {})})

            # ---------- Optional: Ask LLM to clean / enhance formatting ----------
            if content_blocks:
                prompt = (
                    "You are an expert assistant. Take the following content blocks and produce "
                    "a visually clean, concise, user-friendly response. Preserve paragraphs, bullets, "
                    "and topic sections. Do not add extra knowledge.\n\n"
                    f"{content_blocks}"
                )
                try:
                    llm_response = self.llm.chat([{"role": "user", "content": prompt}])
                    llm_text = llm_response.get("content", "").strip()
                    if llm_text:
                        # Replace raw summary block with LLM-enhanced text (truncate to MAX_SUMMARY_CHARS)
                        content_blocks = [{"type": "paragraph", "text": llm_text[:self.MAX_SUMMARY_CHARS]}]
                except Exception as e:
                    # If LLM formatting fails, keep original blocks and log
                    print("LLM formatting step failed in FormatterAgent:", e)
            
            # Log to Mongo
            try:
                self.collection.insert_one({
                    "normalized_query": query,
                    "response": {
                        "summary": raw_summary[:self.MAX_SUMMARY_CHARS],
                        "topics": topics,
                        "raw_extractions": raw_extractions,
                        "content_blocks": content_blocks
                    },
                    "timestamp": datetime.utcnow()
                })
            except Exception as e:
                print("Mongo logging failed in FormatterAgent:", e)

            return {
                "summary": raw_summary[:self.MAX_SUMMARY_CHARS],
                "topics": topics,
                "raw_extractions": raw_extractions,
                "content_blocks": content_blocks
            }

        except Exception as e:
            print("Formatting failed in FormatterAgent:", e)
            # Return a generic, structured error block
            return {
                "summary": "",
                "topics": {},
                "raw_extractions": [],
                "content_blocks": [{"type": "text", "text": "An error occurred while processing your request."}]
            }
