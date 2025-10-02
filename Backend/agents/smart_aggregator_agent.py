import asyncio
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

class SmartAggregatorAgent:
    def __init__(self, llm_client, max_workers=4, max_docs_process=4, max_input_chars=20000, per_doc_timeout=6):
        self.llm = llm_client
        self.max_workers = max_workers
        self.max_docs_process = max_docs_process
        self.max_input_chars = max_input_chars
        self.per_doc_timeout = per_doc_timeout
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def _trim_for_token_limit(self, text: str):
        return text[:self.max_input_chars] if text else ""

    async def _llm_call_async(self, prompt: str):
        loop = asyncio.get_event_loop()
        try:
            reply = await loop.run_in_executor(
                self.executor,
                lambda: self.llm.chat([{"role": "user", "content": prompt}])
            )
            content = reply.get("content", "").strip()
            return content or None
        except Exception:
            return None

    async def _extract_relevant_async(self, query: str, doc: Dict, topic: str):
        raw_content = self._trim_for_token_limit(doc.get("text", "")) or "EMPTY_CONTENT"
        prompt = (
            "Analyze ONLY the content below. Do NOT use external knowledge.\n"
            f"Question: {query}\n\n"
            f"Content:\n{raw_content}\n\n"
            "Relevant Summary:\n"
            "Return ONLY a concise summary if the content is relevant to the question.\n"
            "If the content is NOT relevant to the question, return exactly an empty string, with no quotes or explanation."
        )

        summary = await self._llm_call_async(prompt)
        return {
            "url": doc.get("url", ""),
            "topic": topic,
            "summary": summary,
            "images": (doc.get("images") or [])[:3],
            "title": doc.get("title", ""),
        }

    async def process_documents_async(self, query: str, docs: List[Dict], url_topic_list: List[Dict]):
        url_to_topic = {item["url"]: item.get("topic", "general") for item in url_topic_list}
        docs_to_process = docs[:self.max_docs_process]

        semaphore = asyncio.Semaphore(self.max_workers)

        async def sem_task(doc):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self._extract_relevant_async(query, doc, url_to_topic.get(doc.get("url", ""), "general")),
                        timeout=self.per_doc_timeout
                    )
                except asyncio.TimeoutError:
                    return None

        tasks = [sem_task(doc) for doc in docs_to_process]
        results = [r for r in await asyncio.gather(*tasks) if r and r.get("summary")]
        # print("res_agg",results)
        # Aggregate by topic
        topic_map = {}
        for item in results:
            topic_map.setdefault(item["topic"], []).append(item)

        combined_text = ""
        for topic, items in topic_map.items():
            topic_text = "\n".join(f"- {x['summary']} (URL: {x['url']})" for x in items)
            if topic_text:
                combined_text += f"Topic: {topic}\n{topic_text}\n\n"

        if combined_text.strip():
            # Final aggregation
            final_prompt = (
                f"You are given extracted summaries strictly from provided documents.\n"
                f"User Query: {query}\n\n"
                "Combine ONLY the provided summaries into a single, clear answer.\n"
                "Do NOT use external knowledge.\n\n"
                f"{combined_text}\nFinal Answer:"
            )

            blended_reply = await self._llm_call_async(final_prompt) or "No Relevant information found."
        else:
            blended_reply="No Relevant information found."
        return {"summary": blended_reply.strip()}

    def process_documents(self, query: str, docs: List[Dict], url_topic_list: List[Dict]):
        return asyncio.run(self.process_documents_async(query, docs, url_topic_list))
