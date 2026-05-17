# 🔮 Advanced RAG Explorer — VWO Test Cases

A full **Advanced RAG pipeline** built as an interactive visual explorer.  
Upload your test cases → see chunking → ingest into Qdrant → chat with your data → inspect every step.

---

## 🚀 Quick Start (Windows)

**Option A — One click:**
```
Double-click start.bat
```

**Option B — Manual steps:**
```powershell
# 1. Install dependencies
pip install flask flask-cors pandas openpyxl sentence-transformers qdrant-client rank-bm25 groq nltk numpy

# 2. Generate 5000 test cases CSV
python generate_testcases.py

# 3. Start the app
python app.py
```

Then open → **http://localhost:5001**

---

## 🔑 Groq API Key

1. Get a free key at https://console.groq.com
2. Either:
   - Set env variable: `set GROQ_API_KEY=gsk_...`  
   - Or click **"Set Groq Key"** button in the top-right of the UI

---

## 📋 How to Use

### Stage 1 — Ingest Your Test Cases

| Step | What to do |
|---|---|
| **1. Upload** | Click "Upload File" → drag your CSV/Excel |
| **2. Preview** | Click "Preview Chunks" to see how data is chunked |
| **3. Ingest** | Click "Run Ingestion" → watch progress bar |
| **4. DB Stats** | Click "Qdrant DB Stats" to inspect stored vectors |

### Stage 2 — Chat & Query

| Step | What to do |
|---|---|
| **5. Chat** | Ask questions in the chat interface |
| **6. Trace** | Click "Pipeline Trace" to see every step |

---

## 📁 File Structure

```
ADVANCED_RAG_EXPLAIN/
│
├── app.py                    # Flask server (port 5001)
├── config.py                 # All config (model, paths, params)
├── generate_testcases.py     # Generates 5000 VWO test cases CSV
├── requirements.txt          # Dependencies
├── start.bat                 # One-click setup & run
│
├── pipeline/
│   ├── ingest.py             # CSV/Excel → chunk → embed → Qdrant
│   ├── retriever.py          # Dense + BM25 + RRF fusion
│   ├── reranker.py           # Cross-encoder reranking
│   └── generator.py         # Groq LLM answer generation
│
├── data/
│   └── testcases_vwo.csv     # Generated test cases (5000 rows)
│
├── qdrant_db/                # Auto-created: local Qdrant storage
│
├── templates/
│   └── index.html            # Claude-themed UI
│
├── static/js/
│   └── app.js                # Frontend JavaScript
│
└── concepts/
    └── fusion_and_framework_explained.md
```

---

## ⚙️ Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Embeddings | `all-MiniLM-L6-v2` | 22MB, CPU-fast, already cached |
| Vector DB | **Qdrant** (local file) | No Docker, persistent, production-grade |
| Sparse retrieval | `rank_bm25` | Pure Python BM25 |
| Fusion | RRF (Reciprocal Rank Fusion) | Merges dense + sparse rankings |
| Re-ranker | `ms-marco-MiniLM-L-6-v2` | Cross-encoder, 22MB, fast on CPU |
| LLM | **Groq** `llama3-70b-8192` | Free API, fast inference |
| Server | Flask + Jinja2 | Lightweight Python web framework |
| Frontend | Vanilla JS | No npm/React needed |

---

## 🎨 UI Features

- **Claude dark theme** — warm amber accents on dark charcoal
- **Drag & drop upload** — CSV or Excel
- **Chunk visualizer** — see exact sentence splits, overlap, word counts
- **Ingestion progress bar** — live step-by-step updates
- **Qdrant DB inspector** — browse stored chunks with all metadata
- **Chat interface** — ask questions in natural language
- **6-step pipeline trace** — see every RAG step with scores:
  1. Query embedding (vector preview)
  2. Dense retrieval (Qdrant cosine scores)
  3. Sparse retrieval (BM25 scores)
  4. RRF fusion (merged ranking)
  5. Cross-encoder reranking (kept vs dropped)
  6. LLM generation (token counts, sources)

---

## 📄 CSV Format Expected

Your CSV/Excel should have columns describing test cases. The system will auto-detect all columns and merge them into text for ingestion. The generated `testcases_vwo.csv` uses Jira format:

```
Issue_ID | Issue_Type | Summary | Description | Priority | Status |
Component | Labels | Preconditions | Test_Steps | Expected_Result |
Actual_Result | Test_Data
```
