import os
from typing import Dict, Any
from dotenv import load_dotenv
import openai
import json

load_dotenv()

class FormatterAgent:
    """
    Formats aggregated output for UI/export as structured JSON.
    Optionally polishes with LLM.
    """
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.use_llm and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in .env file for LLM formatting")
        if self.use_llm:
            openai.api_key = self.openai_api_key

    def format(self, aggregated_output: Dict[str, Any]) -> Dict[str, Any]:
        if not aggregated_output:
            return {"tables": [], "timelines": [], "insights": []}
        formatted_output = {
            "tables": aggregated_output.get("tables", []),
            "timelines": aggregated_output.get("timelines", []),
            "insights": aggregated_output.get("insights", [])
        }
        if self.use_llm:
            formatted_output = self.enhance_with_llm(formatted_output)
        print("formt completed")
        return formatted_output

    def enhance_with_llm(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = (
                "You are an expert UI/UX content formatter for dashboards and reports. "
                "You will receive aggregated CI/news data with tables, timelines, and insights. "
                "Polish the data for readability and styling for UI consumption. "
                "Return JSON in the same structure with improved readability.\n"
                f"Data:\n{json.dumps(data, indent=2)}"
            )
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You improve formatting for dashboards and export-ready JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            return result
        except Exception as e:
            print(f"Error during LLM formatting: {e}")
            return data

# # Sample run for debugging/test
# if __name__ == "__main__":
#     agent = FormatterAgent(use_llm=False)
#     sample_output = {
#         "tables": [{"Competitors": ["Tesla", "Rivian"]}],
#         "timelines": [{"date": "2025-09-18", "event": "Tesla model launch"}],
#         "insights": ["Tesla is leading new launches in 2025."]
#     }
#     print(agent.format(sample_output))
