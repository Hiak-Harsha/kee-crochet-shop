import time
import random
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Memory-based rate limiting middleware for sensitive endpoints."""
    def __init__(self, app, limit_sec: int = 60, max_requests: int = 15):
        super().__init__(app)
        self.limit_sec = limit_sec
        self.max_requests = max_requests
        self.history: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Limit OTP requests, logins, and all AI calls to prevent cost abuse/brute force
        if any(p in path for p in ["/auth/login", "/auth/otp/request", "/auth/otp/verify", "/ai/"]):
            client_ip = None
            xff = request.headers.get("x-forwarded-for")
            if xff:
                # Render/Load balancers append real IP first. Split and take the first client address.
                parts = [p.strip() for p in xff.split(",")]
                if parts:
                    client_ip = parts[0]
            if not client_ip:
                client_ip = request.client.host if request.client else "unknown"
                
            key = f"{client_ip}:{path}"
            now = time.time()
            
            # Periodically prune expired rate limit entries to prevent memory leaks (5% chance per request)
            if random.random() < 0.05:
                expired_keys = []
                for k, ts in self.history.items():
                    if not ts or now - ts[-1] > self.limit_sec:
                        expired_keys.append(k)
                for k in expired_keys:
                    self.history.pop(k, None)
            
            # Filter history to keep only requests within the sliding window
            timestamps = self.history.get(key, [])
            timestamps = [t for t in timestamps if now - t < self.limit_sec]
            
            if len(timestamps) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please wait before trying again."}
                )
                
            timestamps.append(now)
            self.history[key] = timestamps

        response = await call_next(request)
        return response
