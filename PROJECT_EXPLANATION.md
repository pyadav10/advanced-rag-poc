# 📘 Project Explanation: Advanced RAG Explorer

This document provides a comprehensive explanation of how the **Advanced RAG Explorer** project works from top to bottom. It breaks down the architecture, the data flow, and the purpose of every major component.

---

## 🎯 What is this project?

The Advanced RAG Explorer is an interactive web application that demonstrates the inner workings of an **Advanced Retrieval-Augmented Generation (RAG)** pipeline. 

Instead of just acting as a "black box" chatbot, this tool is designed for educational and debugging purposes. It works with software testing data (specifically VWO Jira-style test cases) and allows a user to:
1. Upload a dataset.
2. See exactly how the text is chunked and vectorized.
3. Chat with the data.
4. **Trace the pipeline**, viewing exact scores, semantic matches, and keyword matches at every step of the RAG process.

---

## ⚙️ How It Works: The Data Flow

The project is divided into two major phases: **Ingestion** (getting data in) and **Querying** (getting answers out).

### Phase 1: Data Generation & Ingestion
*How files become searchable knowledge.*

1. **Synthetic Data (`generate_testcases.py`)**: To test the system, this script generates 5,000 synthetic VWO test cases in a standard Jira format (Issue ID, Summary, Steps to Reproduce, etc.) and saves it as a CSV in the `data/` folder.
2. **Parsing & Chunking (`pipeline/ingest.py`)**: When the CSV is uploaded via the UI, the system reads the file row by row. It formats the columns into readable paragraphs and then splits them into smaller "chunks" with a bit of overlap so context isn't lost.
3. **Embedding**: Each chunk of text is passed through an embedding model (`all-MiniLM-L6-v2`). This model converts the text into a dense array of numbers (a vector) representing its semantic meaning.
4. **Vector Storage**: These vectors, along with the original text and metadata, are saved locally in a **Qdrant** vector database (stored in the `qdrant_db/` folder).

---

### Phase 2: The Advanced Query Pipeline
*What happens when you ask a question.*

When a user types a question like *"How do I fix the Safari login timeout?"*, the system executes a 5-step process:

1. **Query Embedding**: The user's question is converted into a vector using the exact same embedding model used during ingestion.
2. **Hybrid Retrieval (`pipeline/retriever.py`)**: 
   - **Dense Search**: The system compares the question's vector against all chunks in Qdrant using cosine similarity. This finds chunks with similar *meaning*.
   - **Sparse Search (BM25)**: Simultaneously, the system uses BM25 to look for exact *keyword matches* (e.g., the word "Safari" or "timeout").
3. **Reciprocal Rank Fusion (RRF)**: A mathematical algorithm merges the results of the Dense and Sparse searches. If a chunk ranks highly in *both* meaning and exact keywords, RRF bumps it to the very top.
4. **Cross-Encoder Reranking (`pipeline/reranker.py`)**: The top chunks from RRF are passed to a highly accurate Cross-Encoder model. This model reads the question and the chunk *together* and assigns a final relevance score. Chunks that don't pass the relevance threshold are dropped.
5. **LLM Generation (`pipeline/generator.py`)**: The top 3 surviving, highly-relevant chunks are combined into a prompt with the user's question. This is sent to the **Groq API (Llama 3)**, which reads the context and streams back a human-readable answer.

---

## 🏗️ The Application Architecture

To make this pipeline interactive, we wrap it in a web application.

### Backend (Flask - `app.py`)
- Acts as the web server.
- Provides REST API endpoints:
  - `/api/upload`: Handles file uploads.
  - `/api/ingest`: Triggers the embedding and Qdrant storage.
  - `/api/query`: Triggers the 5-step query pipeline.
- Coordinates between the `pipeline/` scripts and the frontend UI.

### Configuration (`config.py`)
- A central nervous system for the app. It holds all hyperparameters like chunk size, overlap, embedding model names, and API keys. If you want to change the LLM or the vector database settings, you do it here.

### Frontend (Vanilla JS & HTML - `static/` & `templates/`)
- **`templates/index.html`**: The UI skeleton, styled with a sleek dark theme reminiscent of modern AI tools (like Claude).
- **`static/js/app.js`**: Pure JavaScript that handles user interactions. It manages drag-and-drop events, updates progress bars, sends fetch requests to the Flask APIs, streams text from the LLM, and builds the visual "Pipeline Trace" UI cards.

---

## 🚀 Why is this "Advanced"?

A basic RAG pipeline only does **Dense Retrieval** and then generates an answer. 

This pipeline is "Advanced" because it implements:
- **Hybrid Search**: Capturing both semantic intent and exact ID/keyword matches.
- **RRF Fusion**: Intelligently blending multiple search strategies.
- **Cross-Encoder Reranking**: Acting as a strict filter to ensure the LLM doesn't get confused by mildly-related but unhelpful chunks.
- **Full Traceability**: Exposing the "black box" so developers can see the exact math and logic behind why a specific chunk was chosen.
