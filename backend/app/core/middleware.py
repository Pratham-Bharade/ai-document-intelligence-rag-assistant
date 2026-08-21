"""
File: backend/app/core/middleware.py
Purpose: Security Headers, Request Timing Audit Logging, and Sliding Window Rate Limiter Middleware.
"""

import logging
import time
from collections import defaultdict
from typing import Callable, Dict, List
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. SECURITY HEADERS MIDDLEWARE
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends OWASP recommended HTTP Security Headers to every response
    to protect against Clickjacking, MIME-sniffing, XSS, and SSL stripping.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent Clickjacking by disallowing framing
        response.headers["X-Frame-Options"] = "DENY"
        
        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Enforce HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Control referrer information leak
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


# ---------------------------------------------------------------------------
# 2. AUDIT LOGGING & REQUEST TIMING MIDDLEWARE
# ---------------------------------------------------------------------------

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Measures processing duration, adds X-Process-Time header, and logs structured audit events.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        response: Response = await call_next(request)
        
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time"] = f"{process_time_ms}ms"

        client_host = request.client.host if request.client else "unknown"
        logger.info(
            f"[AUDIT] {request.method} {request.url.path} "
            f"status={response.status_code} client={client_host} duration={process_time_ms}ms"
        )
        
        return response


# ---------------------------------------------------------------------------
# 3. SLIDING WINDOW RATE LIMITER MIDDLEWARE
# ---------------------------------------------------------------------------

class SlidingWindowRateLimiter:
    """
    In-memory Sliding Window Rate Limiter tracking timestamps per client IP.
    """
    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old timestamps outside the sliding window
        self.history[client_ip] = [ts for ts in self.history[client_ip] if ts > window_start]

        if len(self.history[client_ip]) >= self.max_requests:
            return False

        self.history[client_ip].append(now)
        return True


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces sliding window rate limits per client IP.
    """
    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exempt health check and docs from rate limiting
        exempt_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
        if any(request.url.path.startswith(p) for p in exempt_paths):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"

        if not self.limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please slow down your requests."}
            )

        return await call_next(request)
