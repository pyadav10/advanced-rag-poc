"""
pipeline/generator.py
──────────────────────
Groq LLM generation using reranked context chunks.
"""

import os
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client = None


def _get_client(api_key: str = ""):
    global _client
    key = api_key or GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
    if not key:
        raise ValueError("GROQ_API_KEY is not set. Provide it in config.py or as env variable.")
    if _client is None:
        _client = Groq(api_key=key)
    return _client


SYSTEM_PROMPT = """You are an expert QA assistant for app.vwo.com.
You are given relevant test case context. Use it to answer the user's question accurately.
If asked to create a new test case, format it clearly with:
  - Title, Preconditions, Steps (numbered), Expected Result, Priority.
If the answer is not in the context, say so honestly.
Keep your response concise and well-structured."""


def generate(query: str, kept_chunks: list[dict], api_key: str = "") -> dict:
    """
    Build context from kept chunks and call Groq.
    Returns answer + prompt metadata for the UI trace.
    """
    client = _get_client(api_key)

    context_parts = []
    for i, ch in enumerate(kept_chunks, start=1):
        src = ch.get("metadata", {}).get("source_id", f"Chunk-{i}")
        context_parts.append(f"[{i}] (Source: {src})\n{ch['text']}")

    context_block = "\n\n---\n\n".join(context_parts)
    user_prompt   = f"Context:\n{context_block}\n\nQuestion: {query}"

    total_context_chars = len(context_block)
    total_context_tokens_est = total_context_chars // 4  # rough estimate

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        model=GROQ_MODEL,
        temperature=0.2,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content
    usage  = response.usage

    return {
        "answer":                  answer,
        "model":                   GROQ_MODEL,
        "context_chunks_used":     len(kept_chunks),
        "context_chars":           total_context_chars,
        "context_tokens_est":      total_context_tokens_est,
        "prompt_tokens":           usage.prompt_tokens if usage else None,
        "completion_tokens":       usage.completion_tokens if usage else None,
        "sources": [
            ch.get("metadata", {}).get("source_id", "unknown")
            for ch in kept_chunks
        ],
    }
