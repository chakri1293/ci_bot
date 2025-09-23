import os
import json
from typing import Dict
from dotenv import load_dotenv
import httpx

load_dotenv()

class FormatterAgent:
  """
  Formats aggregated results into readable, UI-ready content.
  Can create Markdown, plain text, bullet lists, timelines, and tables.
  """

  def __init__(self,llm_client):
    self.llm = llm_client

  def format(self, agg_result: Dict, mode: str, as_markdown: bool = True) -> Dict:
    """
    Input: AggregatorAgent result {"tables":[...],"timelines":[...],"insights":[...]} and mode
    Output: JSON with UI-ready fields: {summary, bullets, markdown, tables, timelines}
    """
    if not any([agg_result.get("tables"), agg_result.get("timelines"), agg_result.get("insights")]):
      return {
        "summary": "No actionable intelligence found.",
        "bullets": [],
        "markdown": "",
        "tables": [],
        "timelines": []
      }


    ui_prompt = (
      "You are a UI format expert bot. Given aggregation output for a competitive intelligence dashboard, "
      "produce the following for the end user:\n"
      "- summary: A single concise paragraph summarizing the entire aggregation in plain English.\n"
      "- bullets: The top 5-7 key insights, as human-readable bullet points.\n"
      "- markdown: Professionally formatted Markdown suitable for dashboard display, showing highlights, any tables as Markdown and timelines as ordered lists, with good use of bold and section headings.\n"
      "- tables: The tables as lists-of-lists, with the first sublist as headers (for export as CSV/XLS).\n"
      "- timelines: Each event in the timeline as a {date, headline, details} dictionary.\n"
      "Do not simply echo the input; reword and distill. Use natural business language and clear structure. Only output valid JSON object."
    )


    try:
      user_content = {
        "mode": mode,
        "tables": agg_result.get("tables", []),
        "timelines": agg_result.get("timelines", []),
        "insights": agg_result.get("insights", []),
      }


      response = self.llm.chat(
        messages=[
          {"role": "system", "content": ui_prompt},
          {"role": "user", "content": json.dumps(user_content)}
        ]
      )
      content = response.get("content", "")
      # Output should be a UI-ready JSON dict
      result = json.loads(content)
      print("format completed")
      # Defensive: fill defaults
      return {
        "summary": result.get("summary", ""),
        "bullets": result.get("bullets", []),
        "markdown": result.get("markdown", ""),
        "tables": result.get("tables", []),
        "timelines": result.get("timelines", [])
      }
    except Exception as e:
      print("Error formatting output:", e)
      insights = agg_result.get("insights", [])
      return {
        "summary": insights[0] if insights else "Formatting failed.",
        "bullets": insights[:5] if insights else [],
        "markdown": "\n".join(insights) if insights else "",
        "tables": agg_result.get("tables", []),
        "timelines": agg_result.get("timelines", [])
      }


# if __name__ == "__main__":
#   from extract_api import FetchAndExtractAgent # your fetch agent import
#   from dedup import DedupAndSummarizeAgent # your dedup agent import
#   from agg import AggregatorAgent


#   fetch_agent = FetchAndExtractAgent()
#   dedup_agent = DedupAndSummarizeAgent()
#   agg_agent = AggregatorAgent()


#   querydata = {"query": "Give me all major product launches in AI tools this month", "mode": "blended"}
#   docs = fetch_agent.fetch_documents(querydata)
#   print('fetch done')
#   dedup_results = dedup_agent.process_documents(docs)
#   print("Final processed documents")
#   agg_result = agg_agent.aggregate(dedup_results, querydata["mode"])
#   print("Aggregated Result done")
#   formatter = FormatterAgent()
#   output = formatter.format(agg_result, querydata["mode"])
#   print("Formatting done")
#   print(json.dumps(output, indent=2))