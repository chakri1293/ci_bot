import os
from typing import List, Dict
from dotenv import load_dotenv
from tavily import TavilyClient
from concurrent.futures import ThreadPoolExecutor, as_completed

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

      # Concurrently extract content
      extract_futures = [
        self.executor.submit(self.extract_content, result.get("url"))
        for result in searchresults if result.get("url")
      ]

      extracted_docs = []
      for future in as_completed(extract_futures):
        doc = future.result()
        if doc and doc.get("text"):
          extracted_docs.append(doc)


      # Optional: Crawl for additional context, shallow crawl for speed
      crawl_futures = [
        self.executor.submit(self.crawl_url, doc.get("url"))
        for doc in extracted_docs if doc.get("url")
      ]


      for future in as_completed(crawl_futures):
        docs = future.result()
        if docs:
          documents.extend(docs)


      documents.extend(extracted_docs)
      print("fetch completed")
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
        search_depth="basic", # for speed; can be 'advanced' as per need
        include_answer=False,
        include_raw_content=True,
        max_results=5,
        auto_parameters=True
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
        extract_depth="basic", # 'basic' for speed
        format="text"
      )
      result = response.get("results", [{}])[0]
      # Some results may fail to fetch content
      if result.get("error"):
        print(f"Failed to fetch content for URL {url}: {result['error']}")
        return {}
      text = result.get("raw_content")
      if not text:
        print(f"No text content extracted for URL {url}")
        return {}


      return {
        "url": result.get("url"),
        "title": result.get("title", "No Title"),
        "text": text,
        "favicon": result.get("favicon"),
        "published_date": result.get("published_date"),
      }
    except Exception as e:
      print(f"Error extracting content for url {url}: {e}")
      return {}


  def crawl_url(self, url: str) -> List[Dict]:
    try:
      response = self.tavilyclient.crawl(url=url, depth=1, max_pages=3)
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
        })
      return crawled_docs
    except Exception as e:
      print(f"Error crawling url {url}: {e}")
      return []


# Example usage/test
# if __name__ == "__main__":
#   agent = FetchAndExtractAgent()
#   querydata = {"query": "Give me all major product launches in AI tools this month", "mode": "blended"}
#   docs = agent.fetch_documents(querydata)
#   print(f"Fetched {len(docs)} documents")
#   for doc in docs:
#     print(f"Title: {doc.get('title')}, URL: {doc.get('url')}")
#     text_snippet = doc.get('text')
#     if text_snippet:
#       print(f"Snippet: {text_snippet[:200]}...\n")
#     else:
#       print("No text snippet available\n")