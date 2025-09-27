from concurrent.futures import ThreadPoolExecutor, as_completed

class SmartAggregatorAgent:
    """
    Ultra-fast topic-aware aggregation with strict token limit.
    Processes raw content from multiple documents in parallel, aggregates by topic,
    and provides a blended visual-rich summary.
    """

    def __init__(self, llm_client, max_workers=6, max_input_chars=20000):
        self.llm = llm_client
        self.max_workers = max_workers
        self.max_input_chars = max_input_chars  # Approx 8192 tokens safe

    def _trim_for_token_limit(self, text):
        return text[:self.max_input_chars] if text else ""

    def _llm_call(self, prompt):
        """Safe wrapper to prevent null or apology/external-knowledge responses."""
        try:
            reply = self.llm.chat([{"role": "user", "content": prompt}])
            content = reply.get("content", "").strip()
            if not content:
                return "NO RESPONSE GENERATED"
            if "sorry" in content.lower() or "external" in content.lower():
                return "NO RELEVANT INFO"
            return content
        except Exception as e:
            return f"LLM ERROR: {str(e)}"

    def _extract_relevant(self, query, doc, topic):
        """
        Step 1: Extract relevant info per doc.
        Forced: Only use given content. No URL or metadata influencing the model.
        """

        # Get raw content safely
        raw_content = doc.get("text", "")
        # ✅ Trim and properly detect empty or whitespace-only content
        raw = self._trim_for_token_limit(raw_content)
        if not raw.strip():  # Handles whitespace-only or accidental blank data
            raw = "EMPTY_CONTENT"

        # Limit number of images used
        images = (doc.get("images") or [])[:3]

        # Optional: Prevent excessive logging output
        # print('raw', raw[:200] + ("..." if len(raw) > 200 else ""))

        # Build prompt without external assumptions
        prompt = (
            "You are an AI assistant. Analyze ONLY the content provided below.\n"
            "Do NOT apologize. Do NOT say external knowledge is required.\n"
            "If the content partially answers the question, summarize ONLY that part.\n"
            "If nothing is relevant, respond exactly with 'NO RELEVANT INFO'.\n\n"
            f"Question: {query}\n\n"
            f"Content:\n{raw}\n\n"
            "Relevant Summary:"
        )

        # LLM call
        extracted = self._llm_call(prompt)
        if not extracted or extracted == "NO RESPONSE GENERATED":
            extracted = "NO RELEVANT INFO"

        # Return consistent structure
        return {
            "url": doc.get("url", ""),
            "topic": topic,
            "summary": extracted,
            "images": images,
            "title": doc.get("title", ""),
        }


    def process_documents(self, query, docs, url_topic_list):
        """
        Full pipeline:
        1. Extract relevant info per doc (parallel)
        2. Aggregate by topic
        3. Generate topic-wise summaries
        4. Generate final blended summary
        """
        url_to_topic = {item["url"]: item.get("topic", "general") for item in url_topic_list}

        # ---------- Step 1: Parallel extraction ----------
        results = []

        if isinstance(docs, dict) and "results" in docs:
            docs_to_process = docs["results"]
        else:
            docs_to_process = docs

        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = [
                ex.submit(self._extract_relevant, query, doc, url_to_topic.get(doc["url"], "general"))
                for doc in docs_to_process
            ]
            for f in as_completed(futures):
                results.append(f.result())

        # print('results',results)

        # ---------- Step 2: Organize results by topic ----------
        topic_map = {}
        for item in results:
            topic_map.setdefault(item["topic"], []).append(item)

        # Combine all extracted summaries into a single input for the LLM
        combined_text = ""
        for topic, items in topic_map.items():
            topic_text = "\n".join(
                f"- {x['summary']} (URL: {x['url']})"
                for x in items
                if x["summary"] != "NO RELEVANT INFO"
            )
            if topic_text:
                combined_text += f"Topic: {topic}\n{topic_text}\n\n"

        # ---------- Step 3: Single LLM call ----------
        if combined_text:
            final_prompt = (
                f"You are given extracted summaries strictly from provided documents.\n"
                f"User Query: {query}\n\n"
                "Your task: Combine ONLY the provided summaries below into a single, clear, and structured answer.\n"
                "STRICT RULES:\n"
                "- Use ONLY the given summaries.\n"
                "- Do NOT bring in external knowledge.\n"
                "- Do NOT apologize or mention missing information.\n"
                "- Preserve bullet points, URLs, and other useful content.\n\n"
                f"{combined_text}\n"
                "Final Answer:"
            )
            blended_reply = self._llm_call(final_prompt)
        else:
            blended_reply = "NO RELEVANT INFORMATION FOUND."

        # ---------- Step 4: Return ----------
        return {
            "summary": blended_reply.strip()
        }
