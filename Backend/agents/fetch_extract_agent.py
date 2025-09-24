import os
from typing import List, Dict
from dotenv import load_dotenv
from tavily import TavilyClient
from concurrent.futures import ThreadPoolExecutor, as_completed, wait

load_dotenv()

class FetchAndExtractAgent:
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
            urls = [res.get("url") for res in searchresults if res.get("url")]
            if not urls:
                continue

            # ✅ Batch extract in one go (much faster than per-URL)
            extract_response = self.tavilyclient.extract(
                urls=urls,
                include_favicon=True,
                extract_depth="basic",
                format="text"
            )

            extracted_docs, crawl_futures = [], []
            for res in extract_response.get("results", []):
                text = res.get("raw_content")
                if text and len(text.strip()) > 50:
                    extracted_docs.append({
                        "url": res.get("url"),
                        "title": res.get("title", "No Title"),
                        "text": text,
                        "favicon": res.get("favicon"),
                        "published_date": res.get("published_date"),
                        "source": "extracted"
                    })
                else:
                    # ✅ Shallow crawl only if extract fails
                    crawl_futures.append(self.executor.submit(self.crawl_url, res.get("url")))

            # Run crawl tasks concurrently with timeout
            crawled_docs = []
            if crawl_futures:
                done, _ = wait(crawl_futures, timeout=2)  # ⏱ max 2 seconds for crawl
                for future in done:
                    docs = future.result()
                    if docs:
                        crawled_docs.extend(docs)

            documents.extend(extracted_docs + crawled_docs)
            print("✅ fetch completed")

        return documents

    def determine_sources(self, mode: str) -> List[str]:
        if mode == "competitor":
            return ["general"]
        if mode == "news":
            return ["news"]
        if mode == "blended":
            return ["general", "news"]
        return []

    def perform_search(self, query: str, topic: str) -> List[Dict]:
        try:
            response = self.tavilyclient.search(
                query=query,
                topic=topic,
                search_depth="basic",  # for speed
                include_answer=False,
                include_raw_content=True,
                max_results=3,
                auto_parameters=True
            )
            return response.get("results", [])
        except Exception as e:
            print(f"Error during search: {e}")
            return []

    def crawl_url(self, url: str) -> List[Dict]:
        try:
            response = self.tavilyclient.crawl(url=url, depth=1, max_pages=1)  # ✅ very shallow
            crawled_docs = []
            for page in response.get("results", []):
                text = page.get("raw_content")
                if not text:
                    continue
                crawled_docs.append({
                    "url": page.get("url"),
                    "title": page.get("title", "No Title"),
                    "text": text,
                    "favicon": page.get("favicon"),
                    "published_date": page.get("published_date"),
                    "source": "crawled"
                })
            return crawled_docs
        except Exception as e:
            print(f"Error crawling url {url}: {e}")
            return []


# # Example usage/test
# if __name__ == "__main__":
#     agent = FetchAndExtractAgent()
#     querydata = {"query": "Give me all major product launches in AI tools this month", "mode": "blended"}
#     docs = agent.fetch_documents(querydata)
#     print(f"Fetched {len(docs)} documents")
#     for doc in docs[:3]:  # show only first 3 for brevity
#         print(f"- [{doc.get('source')}] {doc.get('title')} ({doc.get('url')})")
#         snippet = doc.get('text')
#         if snippet:
#             print(f"  Snippet: {snippet[:150]}...\n")
