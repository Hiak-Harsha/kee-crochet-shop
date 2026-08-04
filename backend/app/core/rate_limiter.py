import time
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
        # Limit OTP requests, logins, and AI chat calls to prevent cost abuse/brute force
        if any(p in path for p in ["/auth/login", "/auth/otp/request", "/auth/otp/verify", "/ai/chat"]):
            client_ip = request.headers.get("x-forwarded-for")
            if client_ip:
                client_ip = client_ip.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"
            key = f"{client_ip}:{path}"
            
            now = time.time()
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
