import os
from typing import List, Dict
from dotenv import load_dotenv
from tavily import TavilyClient
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

class FetchAndExtractAgent:
    """
    Fetches URLs & extracts content using Tavily API based on mode.
    Handles competitor, news, and blended queries, using only valid Tavily topics.
    Processes extraction and crawling concurrently for speed.
    """
    def __init__(self):
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY not set in .env file")
        self.tavilyclient = TavilyClient(api_key=tavily_api_key)
        self.executor = ThreadPoolExecutor(max_workers=10)

    def fetch_documents(self, querydata: Dict) -> List[Dict]:
        query = querydata.get("query")
        mode = querydata.get("mode")
        
        if mode == "irrelevant":
            return []

        sources = self.determine_sources(mode)
        documents = []

        for source in sources:
            searchresults = self.perform_search(query, source)
            # Concurrently process extraction+crawl for each url
            futures = [
                self.executor.submit(self.extract_and_crawl, result.get("url"))
                for result in searchresults if result.get("url")
            ]

            for future in as_completed(futures):
                docs = future.result()
                documents.extend(docs)

        print("document fetched",len(documents))
        return documents

    def extract_and_crawl(self, url: str) -> List[Dict]:
        docs = []
        doc = self.extract_content(url)
        if doc:
            docs.append(doc)
        crawled_docs = self.crawl_url(url)
        if crawled_docs:
            docs.extend(crawled_docs)
        return docs

    def determine_sources(self, mode: str) -> List[str]:
        if mode == "competitor":
            return ["general"]
        if mode == "news":
            return ["news"]
        if mode == "blended":
            return ["general", "news"]
        return []

    def perform_search(self, query: str, source: str) -> List[Dict]:
        try:
            response = self.tavilyclient.search(
                query=query,
                topic=source,
                search_depth="advanced",
                include_answer=False,
                include_raw_content=True,
                max_results=5
            )
            return response.get("results", [])
        except Exception as e:
            print(f"Error during search: {e}")
            return []

    def extract_content(self, url: str) -> Dict:
        try:
            response = self.tavilyclient.extract(
                urls=url,
                include_favicon=True,
                extract_depth="advanced",
                format="text"
            )
            result = response.get("results", [{}])[0]
            return {
                "url": result.get("url"),
                "title": result.get("title", "No Title"),
                "text": result.get("raw_content", ""),
                "metadata": {
                    "favicon": result.get("favicon"),
                    "published_date": result.get("published_date")
                }
            }
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
            return {}

    def crawl_url(self, url: str) -> List[Dict]:
        try:
            response = self.tavilyclient.crawl(url=url, depth=1, max_pages=5)
            crawled_docs = []
            for page in response.get("results", []):
                doc = {
                    "url": page.get("url"),
                    "title": page.get("title", "No Title"),
                    "text": page.get("raw_content", ""),
                    "metadata": {
                        "favicon": page.get("favicon"),
                        "published_date": page.get("published_date")
                    }
                }
                crawled_docs.append(doc)
            return crawled_docs
        except Exception as e:
            print(f"Error crawling url {url}: {e}")
            return []

# Uncomment below to test
# if __name__ == "__main__":
#     agent = FetchAndExtractAgent()
#     sample_querydata = {"query": "What has Competitor X announced this week?", "mode": "competitor"}
#     docs = agent.fetch_documents(sample_querydata)
#     print(docs)
