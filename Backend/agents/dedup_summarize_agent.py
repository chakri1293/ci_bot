import os
from typing import List, Dict
from dotenv import load_dotenv
from tavily import TavilyClient
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
import json

load_dotenv()


def cut_text_to_fit(text: str, max_chars: int = 2000) -> str:
  if len(text) > max_chars:
    return text[-max_chars:]
  return text


class DedupAndSummarizeAgent:
  def __init__(self, llm_client):
    self.llm = llm_client

    self.tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not self.tavily_api_key:
      raise ValueError("TAVILY_API_KEY not set in .env file")
    self.tavilyclient = TavilyClient(api_key=self.tavily_api_key)


    self.executor = ThreadPoolExecutor(max_workers=10)


  def process_documents(self, docs: List[Dict]) -> List[Dict]:
    if not docs:
      return []


    # Limit doc count for speed
    docs = docs[:10]
    uniquedocs = self.deduplicate_docs(docs)
    futures = [self.executor.submit(self.process_single_doc, doc) for doc in uniquedocs]

    results = []
    for fut in as_completed(futures):
      try:
        res = fut.result()
        results.append(res)
      except Exception as e:
        print(f"Error processing document: {e}")


    print("Processed documents count:", len(results))
    return results


  def deduplicate_docs(self, docs: List[Dict]) -> List[Dict]:
    seen_urls, seen_texts, uniquedocs = set(), [], []
    for doc in docs:
      url = doc.get("url")
      text = doc.get("text", "")
      if not url or not text:
        continue
      if url in seen_urls:
        continue
      if any(self.similarity(text, t) > 0.9 for t in seen_texts):
        continue
      seen_urls.add(url)
      seen_texts.append(text)
      uniquedocs.append(doc)
    return uniquedocs


  def similarity(self, a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


  def process_single_doc(self, doc: Dict) -> Dict:
    text = doc.get("text", "")
    url = doc.get("url", "")
    title = doc.get("title", "")
    summary, keypoints = self.summarize_text(text)
    entities = self.extract_entities(url)
    return {
      "url": url,
      "title": title,
      "summary": summary,
      "keypoints": keypoints,
      "entities": entities,
    }


  def summarize_text(self, text: str):
    try:
      text = cut_text_to_fit(text)
      prompt = (
        "You are an expert Competitive Intelligence Analyst. "
        "Summarize the following document concisely and provide key bullet points. "
        "Output JSON with keys: summary, keypoints. "
        f"Document:\n{text}"
      )
      messages = [
        {"role": "system", "content": "You summarize competitive intelligence and market news."},
        {"role": "user", "content": prompt},
      ]
      response = self.llm.chat(
        messages=messages
      )
      content = response.get("content", "")
      try:
        result = json.loads(content)
      except json.JSONDecodeError:
        print("Invalid JSON from LLM; returning truncated text.")
        return text[:200], []
      summary = result.get("summary", "")
      keypoints = result.get("keypoints", [])
      if isinstance(keypoints, str):
        keypoints = [kp.strip() for kp in keypoints.split("\n") if kp.strip()]
      return summary, keypoints
    except Exception as e:
      print(f"Error in summarize_text: {e}")
      return text[:200], []


  def extract_entities(self, url: str):
    try:
      response = self.tavilyclient.map(url=url, map_type="entities")
      return response.get("entities", [])
    except Exception as e:
      print(f"Error in extract_entities for url {url}: {e}")
      return []


# if __name__ == "__main__":
#   from extract_api import FetchAndExtractAgent # your fetch agent import


#   fetch_agent = FetchAndExtractAgent()
#   dedup_agent = DedupAndSummarizeAgent()


#   querydata = {"query": "Give me all major product launches in AI tools this month", "mode": "blended"}
#   docs = fetch_agent.fetch_documents(querydata)
#   print('fetch done')
#   dedup_results = dedup_agent.process_documents(docs)
#   print("Final processed documents:")
#   for doc in dedup_results:
#     print(f"Title: {doc.get('title')}")
#     print(f"Summary: {doc.get('summary')}")
#     print(f"Entities: {doc.get('entities')}")
#     print("---")

