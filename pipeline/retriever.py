"""
pipeline/retriever.py
──────────────────────
Hybrid retrieval: dense (Qdrant) + sparse (BM25) → RRF fusion.
Returns full trace data for the UI pipeline visualizer.
"""

import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import SearchRequest
from rank_bm25 import BM25Okapi
import torch

from config import (
    EMBED_MODEL, QDRANT_PATH, COLLECTION_NAME,
    TOP_K_DENSE, TOP_K_SPARSE, TOP_K_FUSED, RRF_K,
    BM25_FILE
)

torch.set_num_threads(4)
device = "cuda" if torch.cuda.is_available() else "cpu"

# ── Lazy singletons ──────────────────────────────────────
_embedder   = None
_qdrant     = None
_bm25       = None
_bm25_ids   = None
_bm25_texts = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL, device=device)
        _embedder.max_seq_length = 256
    return _embedder


def _get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(path=QDRANT_PATH)
    return _qdrant


def _get_bm25():
    global _bm25, _bm25_ids, _bm25_texts
    if _bm25 is None:
        with open(BM25_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _bm25_ids   = data["ids"]
        _bm25_texts = data["texts"]
        tokenized   = [t.lower().split() for t in _bm25_texts]
        _bm25       = BM25Okapi(tokenized)
    return _bm25, _bm25_ids, _bm25_texts


def reset_singletons():
    """Call after re-ingestion to force reload of BM25 index."""
    global _bm25, _bm25_ids, _bm25_texts, _qdrant
    _bm25 = _bm25_ids = _bm25_texts = _qdrant = None


# ── RRF ─────────────────────────────────────────────────

def rrf(ranks: list[int], k: int = RRF_K) -> float:
    return sum(1.0 / (k + r) for r in ranks)


# ── Main retrieval function ──────────────────────────────

def hybrid_retrieve(query: str) -> dict:
    """
    Returns a trace dict with:
      query_embedding_preview, dense_hits, sparse_hits, fused_hits
    """
    embedder = _get_embedder()
    client   = _get_qdrant()
    bm25, bm25_ids, bm25_texts = _get_bm25()

    # 1. Embed query
    query_vec = embedder.encode([query], normalize_embeddings=True)[0].tolist()
    embed_preview = [round(v, 5) for v in query_vec[:8]]  # first 8 dims for UI

    # 2. Dense retrieval via Qdrant
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vec,
        limit=TOP_K_DENSE,
        with_payload=True,
    )
    dense_response = response.points

    dense_hits = []
    dense_id_to_rank = {}
    for rank, hit in enumerate(dense_response, start=1):
        dense_hits.append({
            "id":         str(hit.id),
            "text":       hit.payload.get("text", ""),
            "metadata":   {k: v for k, v in hit.payload.items() if k != "text"},
            "score":      round(hit.score, 4),
            "rank":       rank,
        })
        dense_id_to_rank[str(hit.id)] = rank

    # 3. Sparse (BM25) retrieval
    tokenized_q = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_q)
    top_sparse_idx = np.argsort(bm25_scores)[::-1][:TOP_K_SPARSE]

    sparse_hits = []
    sparse_id_to_rank = {}
    for rank, idx in enumerate(top_sparse_idx, start=1):
        doc_id = bm25_ids[idx]
        score  = float(bm25_scores[idx])
        sparse_hits.append({
            "id":    doc_id,
            "text":  bm25_texts[idx],
            "score": round(score, 4),
            "rank":  rank,
        })
        sparse_id_to_rank[doc_id] = rank

    # 4. RRF Fusion
    all_ids = set(dense_id_to_rank.keys()) | set(sparse_id_to_rank.keys())
    fused = []
    for doc_id in all_ids:
        d_rank = dense_id_to_rank.get(doc_id, TOP_K_DENSE + 1)
        s_rank = sparse_id_to_rank.get(doc_id, TOP_K_SPARSE + 1)
        rrf_sc = rrf([d_rank, s_rank])

        # Retrieve text/metadata
        text = ""
        metadata = {}
        for h in dense_hits:
            if h["id"] == doc_id:
                text, metadata = h["text"], h["metadata"]
                break
        if not text:
            for h in sparse_hits:
                if h["id"] == doc_id:
                    text = h["text"]
                    break

        fused.append({
            "id":           doc_id,
            "text":         text,
            "metadata":     metadata,
            "dense_rank":   d_rank if doc_id in dense_id_to_rank else None,
            "sparse_rank":  s_rank if doc_id in sparse_id_to_rank else None,
            "dense_score":  dense_id_to_rank.get(doc_id) and next(
                (h["score"] for h in dense_hits if h["id"] == doc_id), None),
            "bm25_score":   sparse_id_to_rank.get(doc_id) and next(
                (h["score"] for h in sparse_hits if h["id"] == doc_id), None),
            "rrf_score":    round(rrf_sc, 6),
        })

    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    fused_hits = fused[:TOP_K_FUSED]

    return {
        "query":                query,
        "embed_preview":        embed_preview,
        "embed_dim":            len(query_vec),
        "dense_hits":           dense_hits,
        "sparse_hits":          sparse_hits,
        "fused_hits":           fused_hits,
        "total_dense_fetched":  len(dense_hits),
        "total_sparse_fetched": len(sparse_hits),
        "total_fused":          len(fused_hits),
    }
