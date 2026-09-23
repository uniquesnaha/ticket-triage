"""Shared rate limiter.

Limits are kept in process memory: on serverless platforms each warm instance counts
separately, so treat these as abuse dampening, not a hard quota. Point
``storage_uri`` at Redis if you need a global limit.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    # Behind Vercel's edge the socket peer is the proxy; Vercel overwrites
    # X-Real-IP with the true client address, so it is safe to trust there (only).
    if get_settings().vercel:
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)
