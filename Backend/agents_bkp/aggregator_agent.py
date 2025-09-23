import os
from typing import List, Dict
import openai
import json
from dotenv import load_dotenv

load_dotenv()

class AggregatorAgent:
    """
    Aggregates summaries & entities, generates actionable insights.
    Branches logic based on mode, outputs structured data.
    """
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in .env file")
        openai.api_key = self.openai_api_key

    def aggregate(self, summarized_docs: List[Dict], mode: str) -> Dict:
        if not summarized_docs:
            print("No summarized docs provided for aggregation.")
            return {"tables": [], "timelines": [], "insights": []}

        combined_text = ""
        for doc in summarized_docs:
            combined_text += (
                f"Title: {doc.get('title')}\n"
                f"Summary: {doc.get('summary')}\n"
                f"Points: {', '.join(doc.get('keypoints', []))}\n"
                f"Entities: {', '.join(doc.get('entities', []))}\n\n"
            )

        system_prompt = (
            "You are an expert Competitive Intelligence Analyst. "
            "Summarized documents with key points and entities are provided. "
            f"Mode: {mode}\n"
            "Generate actionable insights, structured tables, and timelines as a JSON object."
            "Return keys: tables, timelines, insights."
        )
        try:
            print("Calling OpenAI ChatCompletion for aggregation...")
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined_text}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            content = response.choices[0].message.content
            print("Got response from OpenAI.")

            try:
                result = json.loads(content)
            except json.JSONDecodeError as jde:
                print(f"JSON decode error in OpenAI response: {jde}")
                print("Response content was:", content)
                return {"tables": [], "timelines": [], "insights": []}

            tables = result.get("tables", [])
            timelines = result.get("timelines", [])
            insights = result.get("insights", [])

            print("agg completed")
            return {"tables": tables, "timelines": timelines, "insights": insights}
        except Exception as e:
            import traceback
            print("Error during aggregation:")
            traceback.print_exc()
            return {"tables": [], "timelines": [], "insights": []}


# # Sample run for debugging/test
# if __name__ == "__main__":
#     agent = AggregatorAgent()
#     sample_summaries = [
#         {"title": "Tesla Launch", "summary": "Tesla announced new EVs.", "keypoints": ["New models", "Sustainable tech"], "entities": ["Tesla", "EV"], "url": "https://example.com"}
#     ]
#     result = agent.aggregate(sample_summaries, "competitor")
#     print("Aggregation result:", result)
