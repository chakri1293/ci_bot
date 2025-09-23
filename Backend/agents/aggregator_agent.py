import os
import json
from typing import List, Dict
from dotenv import load_dotenv
import httpx

class AggregatorAgent:
  """
  Aggregates processed summaries and entities, generating actionable, mode-specific insights.
  Merges, compares, and structures info for UI display.
  """

  def __init__(self,llm_client):
    self.llm = llm_client

  def aggregate(self, summarized_docs: List[Dict], mode: str) -> Dict:
    if not summarized_docs:
      return {"tables": [], "timelines": [], "insights": []}

    combined_text = ""
    for doc in summarized_docs:
      combined_text += (
        f"TITLE: {doc.get('title', '')}\n"
        f"SUMMARY: {doc.get('summary', '')}\n"
        f"KEYPOINTS: {', '.join(doc.get('keypoints', []))}\n"
        f"ENTITIES: {', '.join(doc.get('entities', []))}\n\n"
      )


    sys_prompt = (
      "You are an expert Competitive Intelligence Aggregator.\n"
      "Given a list of documents, with fields for summary, key points, and entities, perform the following mode-specific aggregation:\n"
      "- Competitor: Compare entries, highlight new products/features, pricing, and emerging trends. Output tables for competitors, products, features. Summarize insights.\n"
      "- News: Generate a timeline of key events with dates if possible, summarize sentiments, and highlight top news points. Output a timeline and event summary.\n"
      "- Blended: Merge competitor and news insights, present comparative summaries, show risks and opportunities. Output merged table, key risks/opportunities, and concise, actionable narrative.\n"
      "Your output must be valid JSON with keys: tables (list), timelines (list), insights (list)."
    )


    try:
      response = self.llm.chat(
        messages=[
          {"role": "system", "content": sys_prompt},
          {
            "role": "user",
            "content": (
              f"MODE: {mode}\n"
              f"DOCUMENTS:\n{combined_text}"
              "\nReturn only valid JSON for UI consumption (keys: tables, timelines, insights)."
            ),
          },
        ]
      )
      content = response.get("content", "")
      result = json.loads(content)
      tables = result.get("tables", [])
      timelines = result.get("timelines", [])
      insights = result.get("insights", [])
      print("Agg completed")
      return {"tables": tables, "timelines": timelines, "insights": insights}
    except Exception as e:
      print("Error in aggregation:", e)
      return {
        "tables": [],
        "timelines": [],
        "insights": [f"Aggregation failed: {e}"],
      }


# if __name__ == "__main__":
#   from extract_api import FetchAndExtractAgent # your fetch agent import
#   from dedup import DedupAndSummarizeAgent # your dedup agent import


#   fetch_agent = FetchAndExtractAgent()
#   dedup_agent = DedupAndSummarizeAgent()
#   agg_agent = AggregatorAgent()


#   querydata = {"query": "Give me all major product launches in AI tools this month", "mode": "blended"}
#   docs = fetch_agent.fetch_documents(querydata)
#   print('fetch done')
#   dedup_results = dedup_agent.process_documents(docs)
#   print("Final processed documents")
#   agg_result = agg_agent.aggregate(dedup_results, querydata["mode"])
#   print("Aggregated Result:",agg_result)
