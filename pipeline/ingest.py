"""
pipeline/ingest.py
──────────────────
Handles CSV/Excel upload → chunking → embedding → Qdrant storage.
Supports preview mode (no storage) and full ingestion mode.
"""

import os
import json
import hashlib
import time
import pandas as pd
import numpy as np
import torch
import nltk
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, OptimizersConfigDiff
)

from config import (
    EMBED_MODEL, EMBED_DIM, QDRANT_PATH, COLLECTION_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP, META_FILE, BM25_FILE
)

torch.set_num_threads(4)
device = "cuda" if torch.cuda.is_available() else "cpu"

# ── NLTK setup ───────────────────────────────────────────
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def make_chunk_id(source_id: str, chunk_index: int) -> str:
    raw = f"{source_id}::{chunk_index}"
    return int(hashlib.md5(raw.encode()).hexdigest(), 16) % (10**12)


def build_text(row: dict, columns: list) -> str:
    """Merge selected columns into a single readable text blob."""
    parts = []
    for col in columns:
        val = str(row.get(col, "")).strip()
        if val and val.lower() not in ("nan", "none", ""):
            parts.append(f"{col}: {val}")
    return "\n".join(parts)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Sentence-aware chunking with overlap.
    Returns list of chunk dicts with text, char_count, word_count, overlap_chars.
    """
    try:
        sentences = nltk.sent_tokenize(text)
    except Exception:
        sentences = [s.strip() for s in text.replace("\n", ". ").split(". ") if s.strip()]

    if not sentences:
        return []

    chunks = []
    current = ""
    current_sents = []

    for sent in sentences:
        if len(current) + len(sent) + 1 <= size:
            current = (current + " " + sent).strip()
            current_sents.append(sent)
        else:
            if current:
                chunks.append(_make_chunk(current, current_sents))
            # Build overlap from tail of previous chunk
            overlap_sents, overlap_text = [], ""
            for s in reversed(current_sents):
                if len(overlap_text) + len(s) + 1 <= overlap:
                    overlap_text = (s + " " + overlap_text).strip()
                    overlap_sents.insert(0, s)
                else:
                    break
            current = (overlap_text + " " + sent).strip()
            current_sents = overlap_sents + [sent]

    if current:
        chunks.append(_make_chunk(current, current_sents))

    # Annotate overlap
    for i, ch in enumerate(chunks):
        if i == 0:
            ch["overlap_chars"] = 0
        else:
            prev = chunks[i - 1]["text"]
            ch["overlap_chars"] = _count_overlap(prev, ch["text"])

    return chunks


def _make_chunk(text: str, sentences: list[str]) -> dict:
    return {
        "text": text,
        "sentences": sentences,
        "sentence_count": len(sentences),
        "char_count": len(text),
        "word_count": len(text.split()),
        "overlap_chars": 0,
    }


def _count_overlap(prev: str, curr: str) -> int:
    """Approximate overlap character count between two adjacent chunks."""
    min_len = min(len(prev), len(curr), CHUNK_OVERLAP * 2)
    for n in range(min_len, 0, -1):
        if prev.endswith(curr[:n]):
            return n
    return 0


# ─────────────────────────────────────────────────────────
# Preview (no storage)
# ─────────────────────────────────────────────────────────

def preview_ingestion(filepath: str, preview_rows: int = 5) -> dict:
    """Parse file → return chunking preview without touching Qdrant."""
    df = _load_file(filepath).fillna("")
    columns = list(df.columns)
    total_rows = len(df)

    sample = df.head(preview_rows).to_dict(orient="records")

    chunk_previews = []
    for i, row in enumerate(sample[:3]):
        text = build_text(row, columns)
        chunks = chunk_text(text)
        chunk_previews.append({
            "row_index": i,
            "source_id": str(list(row.values())[0] if row else f"Row-{i}"),
            "original_text": text,
            "original_char_count": len(text),
            "chunks": chunks,
            "chunk_count": len(chunks),
        })

    avg_chunks = (
        sum(p["chunk_count"] for p in chunk_previews) / len(chunk_previews)
        if chunk_previews else 1
    )

    return {
        "total_rows": total_rows,
        "columns": columns,
        "preview_rows": sample,
        "chunk_previews": chunk_previews,
        "estimated_total_chunks": int(total_rows * avg_chunks),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }


# ─────────────────────────────────────────────────────────
# Full Ingestion
# ─────────────────────────────────────────────────────────

def run_ingestion(filepath: str, progress_cb=None) -> dict:
    """Full pipeline: parse → chunk → embed → store in Qdrant."""

    def emit(payload: dict):
        if progress_cb:
            progress_cb(payload)

    df = _load_file(filepath).fillna("")
    columns = list(df.columns)
    total_rows = len(df)

    emit({"step": "model_load", "message": f"Loading {EMBED_MODEL}…"})
    embedder = SentenceTransformer(EMBED_MODEL, device=device)
    embedder.max_seq_length = 256

    # ── Init Qdrant ──────────────────────────────────────
    os.makedirs(QDRANT_PATH, exist_ok=True)
    client = QdrantClient(path=QDRANT_PATH)

    # Re-create collection for fresh ingestion
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=0),
    )

    # ── Chunk all rows ───────────────────────────────────
    emit({"step": "chunking", "message": "Chunking test cases…"})
    all_ids, all_texts, all_payloads = [], [], []
    chunk_details = []

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        text = build_text(row_dict, columns)
        chunks = chunk_text(text)
        source_id = str(list(row_dict.values())[0] if row_dict else f"Row-{idx}")

        for ci, ch in enumerate(chunks):
            pid = make_chunk_id(source_id, ci)
            payload = {
                "source_id": source_id,
                "chunk_index": ci,
                "total_chunks_in_doc": len(chunks),
                "char_count": ch["char_count"],
                "word_count": ch["word_count"],
                "overlap_chars": ch["overlap_chars"],
                "sentence_count": ch["sentence_count"],
            }
            # Store first 3 column values as searchable payload
            for col in columns[:3]:
                val = str(row_dict.get(col, ""))[:120]
                payload[col.lower().replace(" ", "_")[:20]] = val

            all_ids.append(pid)
            all_texts.append(ch["text"])
            all_payloads.append(payload)
            chunk_details.append({
                "id": str(pid),
                "source_id": source_id,
                "chunk_index": ci,
                "text": ch["text"],
                "char_count": ch["char_count"],
                "word_count": ch["word_count"],
                "overlap_chars": ch["overlap_chars"],
            })

        if (idx + 1) % 100 == 0:
            emit({"step": "chunking_progress", "processed": idx + 1, "total": total_rows})

    total_chunks = len(all_ids)

    # ── Embed ────────────────────────────────────────────
    BATCH = 32
    all_embeddings = []
    emit({"step": "embedding", "total_chunks": total_chunks})

    for i in range(0, total_chunks, BATCH):
        batch_texts = all_texts[i: i + BATCH]
        vecs = embedder.encode(batch_texts, normalize_embeddings=True).tolist()
        all_embeddings.extend(vecs)
        emit({"step": "embedding_progress",
              "embedded": min(i + BATCH, total_chunks),
              "total": total_chunks})

    # ── Store in Qdrant ──────────────────────────────────
    emit({"step": "storing", "message": "Writing to Qdrant…"})
    STORE_BATCH = 256
    for i in range(0, total_chunks, STORE_BATCH):
        points = [
            PointStruct(
                id=all_ids[j],
                vector=all_embeddings[j],
                payload={**all_payloads[j], "text": all_texts[j]},
            )
            for j in range(i, min(i + STORE_BATCH, total_chunks))
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    # Enable indexing now that upload is done
    client.update_collection(
        collection_name=COLLECTION_NAME,
        optimizers_config=OptimizersConfigDiff(indexing_threshold=20000),
    )

    # ── Save metadata + BM25 corpus ──────────────────────
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    embed_dim = len(all_embeddings[0]) if all_embeddings else EMBED_DIM

    meta = {
        "total_test_cases": total_rows,
        "total_chunks": total_chunks,
        "columns": columns,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embed_model": EMBED_MODEL,
        "embed_dim": embed_dim,
        "avg_chunks_per_case": round(total_chunks / total_rows, 2),
        "sample_chunks": chunk_details[:20],
    }
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    with open(BM25_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": [str(x) for x in all_ids], "texts": all_texts}, f, ensure_ascii=False)

    emit({"step": "done", "total_chunks": total_chunks})
    return meta


# ─────────────────────────────────────────────────────────
# Util
# ─────────────────────────────────────────────────────────

def _load_file(filepath: str) -> pd.DataFrame:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return pd.read_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(filepath)
    raise ValueError(f"Unsupported file type: {ext}")
