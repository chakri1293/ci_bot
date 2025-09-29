# agents/tavily_crawl_agent.py
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

class TavilyCrawlAgent:
    """
    Iteratively crawls URLs using Tavily client (no batch support).
    Matches ExtractAgent signature: returns (results, original_input)
    """

    def __init__(self, tavily_client, max_urls: int = 5, max_workers: int = 3):
        """
        tavily_client: shared TavilyClient instance
        max_urls: limit number of URLs to process for speed
        max_workers: small thread pool for concurrency
        """
        self.client = tavily_client
        self.max_urls = max_urls
        self.max_workers = max_workers

    def crawl(self, urls_with_topics: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Crawl URLs and return:
            1. List of crawled documents
            2. Original urls_with_topics (unchanged)
        """
        print("crawl started")
        if not urls_with_topics:
            return [], urls_with_topics

        subset = urls_with_topics[: self.max_urls]
        results = []

        if self.max_workers > 1 and len(subset) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_item = {
                    executor.submit(self._crawl_single, item["url"], item.get("topic", "general")): item
                    for item in subset
                }
                for future in as_completed(future_to_item):
                    try:
                        docs = future.result()
                        results.extend(docs)
                    except Exception as e:
                        print(f"Error crawling {future_to_item[future]['url']}: {e}")
        else:
            for item in subset:
                docs = self._crawl_single(item["url"], item.get("topic", "general"))
                results.extend(docs)

        print("crawl done")
        return results

    def _crawl_single(self, url: str, topic: str) -> List[Dict]:
        """
        Individual crawl with strict limits for speed.
        """
        try:
            response = self.client.crawl(
                url=url,      
                limit=10,
            )

            docs = []
            for page in response.get("results", []):
                text = page.get("raw_content")
                if not text or len(text.strip()) < 50:
                    continue

                docs.append({
                    "url": page.get("url"),
                    "text": text,
                    "favicon": page.get("favicon", []),
                    "images": page.get("images", []),
                    "topic": topic,
                    "source": "crawled"
                })

            return docs

        except Exception as e:
            print(f"Error in _crawl_single for {url}: {e}")
            return []