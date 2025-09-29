import asyncio
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()
tavily_api_key = os.getenv("TAVILY_API_KEY")
tavilyclient = TavilyClient(api_key=tavily_api_key)

async def crawl_url(url, max_pages=1):
    try:
        response = tavilyclient.crawl(url=url, depth=1, max_pages=max_pages)
        docs = []
        for page in response.get("results", []):
            text = page.get("raw_content")
            if not text:
                continue
            docs.append({
                "url": page.get("url"),
                "title": page.get("title", "No Title"),
                "text": text,
                "favicon": page.get("favicon"),
                "published_date": page.get("published_date"),
                "source": "crawled"
            })
        return docs
    except Exception as e:
        print(f"⚠️ Crawl failed for {url}: {e}")
        return []

async def fetch_and_process(query: str, max_results: int = 5, crawl_if_needed=True):
    # Step 1: Search
    search_response = tavilyclient.search(
        query=query,
        topic="news",
        search_depth="basic",
        include_answer=False,
        include_raw_content=True,
        max_results=max_results,
        auto_parameters=True
    )
    urls = [item["url"] for item in search_response.get("results", []) if "url" in item]
    if not urls:
        return []

    # Step 2: Extract all URLs at once (FAST)
    extract_response = tavilyclient.extract(
        urls=urls,
        include_favicon=True,
        extract_depth="basic",
        format="text"
    )

    extracted_docs, crawl_tasks = [], []
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
        elif crawl_if_needed:
            # schedule async crawl fallback
            crawl_tasks.append(crawl_url(res.get("url")))

    # Run all crawls concurrently with timeout
    crawled_docs = []
    if crawl_tasks:
        try:
            results = await asyncio.wait_for(asyncio.gather(*crawl_tasks), timeout=3)
            for r in results:
                crawled_docs.extend(r)
        except asyncio.TimeoutError:
            print("⏱️ Crawl fallback timed out, returning only extracted docs.")

    return extracted_docs + crawled_docs


# 🔹 Example run (sync wrapper for testing)
if __name__ == "__main__":
    query = "Recent news about the opening of new Microsoft offices"
    results = asyncio.run(fetch_and_process(query, max_results=5))
    for r in results:
        print(f"- [{r['source']}] {r['title']} ({r['url']})")
