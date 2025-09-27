# agents/tavily_crawl_agent.py
from typing import List, Dict, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

class TavilyCrawlAgent:
    """
    Crawls URLs using a shared Tavily client, concurrently but yields results one by one.
    """

    def __init__(self, tavily_client, max_workers: int = 5):
        """
        tavily_client: a shared instance of TavilyClient passed from outside
        max_workers: number of threads for concurrent crawling
        """
        self.client = tavily_client
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def crawl(self, urls_with_topics: List[Dict]) -> Generator[Dict, None, None]:
        """
        Crawl URLs concurrently but yield results one by one as they finish.

        urls_with_topics: List of dicts like:
            [{"url": "http://...", "topic": "news"}, {"url": "http://...", "topic": "general"}]
        """
        print("crawl started")
        if not urls_with_topics:
            return

        futures = {
            self.executor.submit(self._crawl_single, item["url"], item.get("topic", "general")): item["url"]
            for item in urls_with_topics
        }

        for future in as_completed(futures):
            try:
                results = future.result()
                for doc in results:
                    yield doc
            except Exception as e:
                url = futures[future]
                print(f"Error crawling {url}: {e}")

        print("crawl done")

    def _crawl_single(self, url: str, topic: str) -> List[Dict]:
        """
        Crawl a single URL and return a list of document dicts.
        """
        try:
            response = self.client.crawl(url=url, depth=1, max_pages=1)
            docs = []
            for page in response.get("results", []):
                text = page.get("raw_content")
                if not text or len(text.strip()) < 50:
                    continue
                docs.append({
                    "url": page.get("url"),
                    "text": text,
                    "favicon": page.get("favicon",[]),
                    "images": page.get("images", []),
                    "topic": topic,
                    "source": "crawled"
                })
            return docs
        except Exception as e:
            print(f"Error in _crawl_single for {url}: {e}")
            return []
