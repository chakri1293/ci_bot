# agents/tavily_extract_agent.py
from typing import List, Dict, Tuple

class TavilyExtractAgent:
    """
    Extracts content from URLs using a shared Tavily client.
    """

    def __init__(self, tavily_client):
        """
        tavily_client: a shared instance of TavilyClient passed from outside
        """
        self.client = tavily_client

    def extract(self, urls_with_topics: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Extract content from all URLs at once and return:
            1. List of extracted results
            2. Original urls_with_topics list (unchanged)

        urls_with_topics: List of dicts like:
            [{"url": "http://...", "topic": "news"}, {"url": "http://...", "topic": "general"}]
        """
        print("extract started")
        if not urls_with_topics:
            return [], urls_with_topics

        # Gather all URLs in one list
        urls = [item["url"] for item in urls_with_topics]

        # Call extract once
        response = self.client.extract(
            urls=urls,  # pass list of URLs at once
            include_favicon=False,
            include_images=False,
            extract_depth="basic",
            format="markdown"
        )

        results = []
        res_list = response.get("results", [])

        # Attach topics by matching URL back to urls_with_topics
        for res in res_list:
            url = res.get("url")
            text = res.get("raw_content")

            # Skip invalid content
            if not text or len(text.strip()) <= 50:
                continue

            # Find topic for this URL
            topic = next((x.get("topic", "general") for x in urls_with_topics if x["url"] == url), "general")

            results.append({
                "url": url,
                "text": text,
                "favicon": res.get("favicon", []),
                "images": res.get("images", []),
                "topic": topic,
                "source": "extracted"
            })

        print("extract done")
        return results