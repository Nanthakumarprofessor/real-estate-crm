"""
Root entry point.

Runs the FastAPI application using uvicorn.

Usage:
    # From the backend/ directory:
    uv run python main.py

    # Or directly with uvicorn:
    uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,       # auto-reload on file changes (development)
        log_level="info",
    )
