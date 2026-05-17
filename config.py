import os
from dotenv import load_dotenv

load_dotenv()

# ── Embedding ────────────────────────────────────────────
EMBED_MODEL  = "all-MiniLM-L6-v2"   # 22MB, fast on CPU, already downloaded
EMBED_DIM    = 384                   # output dims for all-MiniLM-L6-v2

# ── Re-Ranker ────────────────────────────────────────────
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ── Qdrant (local file-based, no Docker needed) ──────────
QDRANT_PATH      = "./qdrant_db"
COLLECTION_NAME  = "advanced_rag"

# ── Chunking ─────────────────────────────────────────────
CHUNK_SIZE    = 400   # characters per chunk
CHUNK_OVERLAP = 80    # overlap between adjacent chunks

# ── Retrieval ────────────────────────────────────────────
TOP_K_DENSE  = 10
TOP_K_SPARSE = 10
TOP_K_FUSED  = 5
TOP_K_RERANK = 3
RRF_K        = 60    # RRF constant

# ── LLM ──────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── Paths ────────────────────────────────────────────────
DATA_DIR  = "./data"
META_FILE = "./qdrant_db/ingest_meta.json"
BM25_FILE = "./qdrant_db/bm25_corpus.json"
