"""
pipeline/reranker.py
─────────────────────
Cross-encoder re-ranking of fused hits.
Returns scored, sorted, and annotated results for the UI trace.
"""

import torch
from sentence_transformers import CrossEncoder
from config import RERANK_MODEL, TOP_K_RERANK

torch.set_num_threads(4)

_cross_encoder = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(RERANK_MODEL, max_length=512)
    return _cross_encoder


def rerank(query: str, fused_hits: list[dict]) -> dict:
    """
    Score each fused hit with the cross-encoder.
    Returns kept (top-K) and dropped chunks with their scores.
    """
    if not fused_hits:
        return {"kept": [], "dropped": [], "total_input": 0, "total_kept": 0}

    model = _get_cross_encoder()

    pairs  = [(query, hit["text"]) for hit in fused_hits]
    scores = model.predict(pairs).tolist()

    scored = []
    for hit, score in zip(fused_hits, scores):
        scored.append({**hit, "rerank_score": round(float(score), 4)})

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)

    kept    = scored[:TOP_K_RERANK]
    dropped = scored[TOP_K_RERANK:]

    return {
        "kept":        kept,
        "dropped":     dropped,
        "total_input": len(fused_hits),
        "total_kept":  len(kept),
    }
