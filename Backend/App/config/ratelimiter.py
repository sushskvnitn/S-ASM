# app/config/ratelimiter.py
import asyncio
import time

class RateLimiter:
    def __init__(self, rate_limit=5, interval=1.0):
        self.rate_limit = rate_limit  # Requests
        self.interval = interval      # Seconds
        self.tokens = rate_limit
        self.last_check = time.monotonic()

    async def acquire(self):
        while self.tokens <= 0:
            now = time.monotonic()
            elapsed = now - self.last_check
            self.tokens += elapsed * (self.rate_limit / self.interval)
            self.last_check = now
            await asyncio.sleep(0.1)
        self.tokens -= 1

# Usage
rate_limiter = RateLimiter(rate_limit=10, interval=1.0)

