# app/core/scanners/ssrf.py
import aiohttp
import asyncio
from app.config.headers import get_rotated_headers
from app.config.ratelimiter import rate_limiter
from app.core.validator import validate_response

INTERNAL_TARGETS = [
    "http://127.0.0.1",
    "http://localhost",
    "http://169.254.169.254",  # AWS metadata
]

# You can replace with your own webhook.site listener ID
WEBHOOK_OOB = "https://<your-id>.webhook.site"

async def scan(url):
    findings = []

    async with aiohttp.ClientSession() as session:
        for target in INTERNAL_TARGETS + [WEBHOOK_OOB]:
            await rate_limiter.acquire()
            test_url = f"{url}?url={target}"

            try:
                async with session.get(test_url, headers=get_rotated_headers(), timeout=10) as resp:
                    body = await resp.text()
                    if resp.status in [200, 302] and validate_response(target, resp):
                        findings.append({
                            "vulnerability": "SSRF",
                            "payload": test_url,
                            "target_accessed": target,
                            "status": resp.status,
                            "indicators": body[:200]
                        })
            except Exception:
                continue

    return findings
