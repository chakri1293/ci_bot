import os
from typing import List, Dict
from dotenv import load_dotenv
from tavily import TavilyClient
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
import openai
import json

load_dotenv()

def cut_text_to_fit(text, max_chars=3000):
    """Trim text to fit model input limits."""
    if len(text) > max_chars:
        return text[-max_chars:]
    return text

class DedupAndSummarizeAgent:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in .env file")
        openai.api_key = self.openai_api_key

        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY not set in .env file")
        self.tavilyclient = TavilyClient(api_key=self.tavily_api_key)

        self.executor = ThreadPoolExecutor(max_workers=5)

    def process_documents(self, docs: List[Dict]) -> List[Dict]:
        if not docs:
            return []
        uniquedocs = self.deduplicate_docs(docs)

        futures = [self.executor.submit(self.process_single_doc, doc) for doc in uniquedocs]
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error processing a document: {e}")

        print("processed the documents", results)
        return results

    def deduplicate_docs(self, docs: List[Dict]) -> List[Dict]:
        seentexts, seenurls = [], set()
        uniquedocs = []
        for doc in docs:
            url = doc.get("url")
            text = doc.get("text", "")
            if not text or not url:
                continue
            if url in seenurls:
                continue
            seenurls.add(url)
            if any(self.similarity(text, t) > 0.9 for t in seentexts):
                continue
            seentexts.append(text)
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
            "entities": entities
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
                {"role": "user", "content": prompt}
            ]

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            content = response.choices[0].message.content
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                print("Warning: invalid JSON from LLM, returning raw text summary")
                return text[:200], []

            summary = result.get("summary", "")
            keypoints = result.get("keypoints", [])
            if isinstance(keypoints, str):
                keypoints = [kp.strip() for kp in keypoints.split("\n") if kp.strip()]
            return summary, keypoints
        except Exception as e:
            print(f"Error during summarization: {e}")
            return text[:200], []

    def extract_entities(self, url: str):
        try:
            # Pass 'url' to map to extract entities
            response = self.tavilyclient.map(url=url, map_type="entities")
            entities = response.get("entities", [])
            return entities
        except Exception as e:
            print(f"Error during entity extraction: {e}")
            return []


# Uncomment to test
# if __name__ == "__main__":
#     agent = DedupAndSummarizeAgent()
#     sample_docs = [
#         {"url": "https://example.com", "title": "Tesla Launch", "text": "Tesla announced new EV models."}
#     ]
#     result = agent.process_documents(sample_docs)
#     print(result)
