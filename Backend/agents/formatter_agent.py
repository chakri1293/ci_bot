from typing import Dict, List

class FormatterAgent:
    """
    Formats the aggregated results for final user response.
    Ensures readability, preserves bullets, numbered lists, paragraphs, and relevant URLs.
    """

    MAX_SUMMARY_CHARS = 2000  # truncate summary to avoid overly long text
    MAX_BULLETS = 10  # max bullets to show

    def __init__(self, llm_client):
        """
        llm_client: a client with a chat() method that accepts messages
        [{"role": "user", "content": "..."}] and returns a dict with 'content'.
        """
        self.llm = llm_client

    def format(self, agg_result: Dict) -> Dict:
        """
        Formats aggregated result into a rich, user-facing response.
        agg_result may contain:
        - summary: raw combined summary text
        - topics: dict of topic-wise summaries
        - raw_extractions: list of extracted content per document
        """
        if not agg_result or "summary" not in agg_result:
            return {"summary": "No relevant information found."}

        raw_summary = agg_result.get("summary", "").strip()
        topics = agg_result.get("topics", {})
        raw_extractions = agg_result.get("raw_extractions", [])

        # ---------- Build topic hints for user ----------
        topic_sections = []
        for topic, text in topics.items():
            if text and text != "NO RELEVANT INFO":
                topic_sections.append(f"### {topic}\n{text}")

        topic_text = "\n\n".join(topic_sections)

        # ---------- Combine for final LLM prompt ----------
        final_input = raw_summary
        if topic_text:
            final_input += "\n\n" + "Topic-wise insights:\n" + topic_text

        # ---------- LLM call to produce final user-friendly response ----------
        try:
            prompt = (
                "You are an expert assistant. Produce a concise, readable response to the user query, "
                "based only on the content below. Preserve bullets, numbered lists, paragraphs, and URLs. "
                "Do not add external knowledge. Keep it clear and structured for easy reading.\n\n"
                f"{final_input}"
            )
            response = self.llm.chat([{"role": "user", "content": prompt}])
            final_summary = response.get("content", "").strip()
        except Exception as e:
            print("LLM formatting failed:", e)
            final_summary = final_input[:self.MAX_SUMMARY_CHARS]

        # ---------- Truncate if too long ----------
        if len(final_summary) > self.MAX_SUMMARY_CHARS:
            final_summary = final_summary[:self.MAX_SUMMARY_CHARS]

        # ---------- Return final structured response ----------
        return {
            "summary": final_summary,
            "topics": topics,  # optional: can be used in UI hover or details
            "raw_extractions": raw_extractions
        }
