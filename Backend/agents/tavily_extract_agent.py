from typing import List, Dict, Tuple
from tavily import TavilyClient

class TavilyExtractAgent:
    """
    Extracts content from URLs using a shared Tavily client.
    """

    def __init__(self, tavily_client: TavilyClient):
        """
        tavily_client: an instance of TavilyClient passed from outside
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
        # print("Extract started")

        if not urls_with_topics:
            return [], urls_with_topics

        # Gather all URLs in one list
        urls = [item["url"] for item in urls_with_topics]
        # print('urls',urls)
        try:
            # Call extract once
            response = self.client.extract(
                urls=urls,
                include_favicon=False,
                include_images=False,
                extract_depth="basic",
                format="markdown"
            )
            # print('extract_actual_response',response)

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

            # print("Extract done")
            return results

        except Exception as e:
            print(f"Error during extraction: {e}")
            return []
