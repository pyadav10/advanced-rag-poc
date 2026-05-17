@echo off
title Advanced RAG Explorer — Setup ^& Run
color 0A
echo.
echo  ============================================
echo   Advanced RAG Explorer — VWO Test Cases
echo   Qdrant + MiniLM + BM25 + Groq
echo  ============================================
echo.

:: Step 1 — Install dependencies
echo [1/3] Installing Python dependencies...
pip install flask flask-cors pandas openpyxl sentence-transformers qdrant-client rank-bm25 groq nltk numpy
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: pip install failed. Make sure Python is installed and in PATH.
    pause
    exit /b 1
)
echo.
echo  ✓ Dependencies installed.
echo.

:: Step 2 — Generate test cases CSV
echo [2/3] Generating 5000 VWO test cases CSV...
python generate_testcases.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Could not generate test cases. Check generate_testcases.py
    pause
    exit /b 1
)
echo.
echo  ✓ testcases_vwo.csv created in ./data/
echo.

:: Step 3 — Start Flask server
echo [3/3] Starting Advanced RAG Explorer...
echo.
echo  Open your browser at:  http://localhost:5001
echo  Press Ctrl+C to stop.
echo.
python app.py

pause
