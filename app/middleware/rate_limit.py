import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from quart import Response, current_app
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, limit, per_seconds):
        self.limit = limit
        self.per_seconds = per_seconds
        self.requests = defaultdict(list)

    async def is_allowed(self, client_ip):
        now = datetime.utcnow()
        # Remove requests older than the time window
        self.requests[client_ip] = [
            timestamp for timestamp in self.requests[client_ip]
            if now - timestamp < timedelta(seconds=self.per_seconds)
        ]
        # Check if request count exceeds limit
        if len(self.requests[client_ip]) >= self.limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {len(self.requests[client_ip])} requests")
            return False
        # Add new request timestamp
        self.requests[client_ip].append(now)
        return True

class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Handle lifespan events
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        # Handle HTTP requests
        if scope["type"] == "http":
            # Parse rate limit from config (e.g., "100 per minute")
            rate_limit_str = current_app.config.get("RATE_LIMIT", "100 per minute")
            try:
                limit, per = rate_limit_str.split(" per ")
                limit = int(limit)
                per = {"minute": 60, "hour": 3600, "day": 86400}.get(per, 60)
            except ValueError:
                logger.error(f"Invalid RATE_LIMIT format: {rate_limit_str}, defaulting to 100 per minute")
                limit, per = 100, 60

            rate_limiter = RateLimiter(limit, per)
            client_ip = scope.get("client", ["unknown"])[0]

            if not await rate_limiter.is_allowed(client_ip):
                response = Response(
                    {"error": "Rate limit exceeded"},
                    status=429,
                    headers={"Retry-After": str(per)}
                )
                await response(scope, receive, send)
                return

            await self.app(scope, receive, send)
            return

        # Pass through other scope types
        await self.app(scope, receive, send)