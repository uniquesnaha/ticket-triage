"""Vercel Python serverless entrypoint.

vercel.json rewrites /api/* here; the ASGI app sees the original path (/api/v1/...).
All application code lives in backend/app.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

__all__ = ["app"]
