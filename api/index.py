"""Vercel Serverless Function entrypoint for FastAPI."""
import os
import sys

# Ensure backend directory is in Python path for module resolution
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app  # noqa: E402
