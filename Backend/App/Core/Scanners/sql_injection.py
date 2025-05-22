# app/core/scanners/sql_injection.py
import aiohttp
import asyncio
import time
from app.config.headers import get_rotated_headers
from app.config.ratelimiter import rate_limiter
from app.core.validator import validate_response

SQL_ERRORS = [
    "You have an error in your SQL syntax",
    "Warning: mysql_fetch",
    "Unclosed quotation mark after the character string",
    "Microsoft OLE DB Provider for SQL Server",
    "supplied argument is not a valid MySQL result"
]

BOOLEAN_PAYLOADS = [
    ("1=1", "1=2"),
    ("' OR '1'='1", "' OR '1'='2"),
    ("admin'--", "admin' AND 1=2--"),
]

TIME_PAYLOAD = "' OR SLEEP(5)--"

async def scan(url):
    findings = []

    async with aiohttp.ClientSession() as session:
        # Boolean-based SQLi
        for true_payload, false_payload in BOOLEAN_PAYLOADS:
            await rate_limiter.acquire()
            try:
                true_url = f"{url}?id={true_payload}"
                false_url = f"{url}?id={false_payload}"

                async with session.get(true_url, headers=get_rotated_headers(), timeout=10) as true_resp, \
                           session.get(false_url, headers=get_rotated_headers(), timeout=10) as false_resp:

                    true_text = await true_resp.text()
                    false_text = await false_resp.text()

                    if abs(len(true_text) - len(false_text)) > 100:
                        findings.append({
                            "vulnerability": "SQL Injection (Boolean-Based)",
                            "payload_true": true_url,
                            "payload_false": false_url,
                            "status": (true_resp.status, false_resp.status)
                        })
            except Exception:
                continue

        # Error-based SQLi
        payload = "'"
        test_url = f"{url}?id={payload}"
        await rate_limiter.acquire()

        try:
            async with session.get(test_url, headers=get_rotated_headers(), timeout=10) as resp:
                body = await resp.text()
                for error in SQL_ERRORS:
                    if error in body:
                        findings.append({
                            "vulnerability": "SQL Injection (Error-Based)",
                            "payload": test_url,
                            "status": resp.status,
                            "error_signature": error
                        })
        except Exception:
            pass

        # Time-based SQLi
        await rate_limiter.acquire()
        try:
            start = time.time()
            time_url = f"{url}?id={TIME_PAYLOAD}"
            async with session.get(time_url, headers=get_rotated_headers(), timeout=10) as resp:
                elapsed = time.time() - start
                if elapsed > 4.5:
                    findings.append({
                        "vulnerability": "SQL Injection (Time-Based)",
                        "payload": time_url,
                        "status": resp.status,
                        "response_time": elapsed
                    })
        except Exception:
            pass

    return findings
