"""
app.py  —  Advanced RAG Explorer (Flask server)
"""

import logging
import os
import json
import threading
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from pipeline.ingest    import preview_ingestion, run_ingestion
from pipeline.retriever import hybrid_retrieve, reset_singletons
from pipeline.reranker  import rerank
from pipeline.generator import generate
from config import DATA_DIR, META_FILE, GROQ_API_KEY

app = Flask(__name__)
# Security: Restrict CORS to localhost and the app's own port
CORS(app, origins=["http://127.0.0.1:5000", "http://localhost:5000"])

# Security: Limit file upload size to 16MB to prevent OOM/DoS
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(DATA_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
app.logger.setLevel(logging.INFO)

# ── In-memory ingestion progress tracker ─────────────────
_progress: dict = {"running": False, "steps": [], "done": False, "error": None, "result": None}
_progress_lock  = threading.Lock()


def _progress_cb(payload: dict):
    app.logger.info("INGEST PROGRESS: %s", payload)
    with _progress_lock:
        _progress["steps"].append(payload)


# ─────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─────────────────────────────────────────────────────────
# Stage 1 — Ingestion
# ─────────────────────────────────────────────────────────

@app.route("/api/preview", methods=["POST"])
def api_preview():
    """Upload file → return chunking preview without storing."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f    = request.files["file"]
    path = os.path.join(DATA_DIR, f.filename)
    f.save(path)

    try:
        preview = preview_ingestion(path, preview_rows=5)
        return jsonify(preview)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/process_data", methods=["POST"])
def api_process_data():
    """Start full ingestion in a background thread."""
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found on server. Please upload again."}), 400

    with _progress_lock:
        _progress["running"] = True
        _progress["steps"]   = []
        _progress["done"]    = False
        _progress["error"]   = None
        _progress["result"]  = None

    def worker():
        app.logger.info("Starting ingestion for %s", path)
        try:
            result = run_ingestion(path, progress_cb=_progress_cb)
            reset_singletons()
            with _progress_lock:
                _progress["result"] = result
                _progress["done"]   = True
                _progress["running"] = False
        except Exception as e:
            app.logger.error("Ingestion error: %s", e, exc_info=True)
            with _progress_lock:
                _progress["error"]   = str(e)
                _progress["done"]    = True
                _progress["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/process_data/progress", methods=["GET"])
def api_process_data_progress():
    with _progress_lock:
        return jsonify(dict(_progress))


@app.route("/api/db-stats", methods=["GET"])
def api_db_stats():
    """Return metadata about the current Qdrant collection."""
    if not os.path.exists(META_FILE):
        return jsonify({"error": "Not ingested yet"}), 404
    with open(META_FILE, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


# ─────────────────────────────────────────────────────────
# Stage 2 — Query / Chat
# ─────────────────────────────────────────────────────────

@app.route("/api/query", methods=["POST"])
def api_query():
    """Full RAG pipeline: retrieve → rerank → generate. Returns complete trace."""
    data  = request.get_json(force=True)
    query = data.get("query", "").strip()
    api_key = data.get("groq_api_key", "") or GROQ_API_KEY

    if not query:
        return jsonify({"error": "query is required"}), 400

    if not os.path.exists(META_FILE):
        return jsonify({"error": "Please ingest documents first."}), 400

    try:
        t0 = time.time()

        # Step 1 — Hybrid retrieval
        retrieval_trace = hybrid_retrieve(query)

        # Step 2 — Re-rank
        rerank_trace = rerank(query, retrieval_trace["fused_hits"])

        # Step 3 — Generate
        gen_result = generate(query, rerank_trace["kept"], api_key=api_key)

        elapsed = round(time.time() - t0, 2)

        return jsonify({
            "query":          query,
            "retrieval":      retrieval_trace,
            "reranking":      rerank_trace,
            "generation":     gen_result,
            "elapsed_sec":    elapsed,
        })

    except ValueError as e:
        return jsonify({"error": str(e), "hint": "Set GROQ_API_KEY"}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/set-key", methods=["POST"])
def api_set_key():
    """Allow the user to provide the Groq API key at runtime."""
    global GROQ_API_KEY
    import config as cfg
    data = request.get_json(force=True)
    key  = data.get("key", "").strip()
    if not key:
        return jsonify({"error": "key is required"}), 400
    cfg.GROQ_API_KEY = key
    os.environ["GROQ_API_KEY"] = key
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🔮 Advanced RAG Explorer — http://localhost:5001\n")
    app.logger.info("Advanced RAG Explorer starting on port 5001")
    # Security: Default to debug=False. Use environment variable for local development.
    is_debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="127.0.0.1", port=5001, debug=is_debug, use_reloader=False)
