"""
scanner_tasks.py
Celery tasks that orchestrate a full ASM scan pipeline.

Import chain (no circular imports):
    asm_tasks  →  (no app imports)
    celery_worker  →  asm_tasks, scanner_tasks
    scanner_tasks  →  asm_tasks  (celery app only)
"""

import asyncio
import json
import logging
import shutil

from asm_tasks import celery  # import the Celery app directly — breaks the circular chain
from Modules.dirbuster import smart_crawler
from Modules.js_crawler import js_linkfinder
from Modules.vulnscan import run_nuclei_scan_sync  # use the sync wrapper
from Core.Utils import save_output

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subfinder helpers
# ---------------------------------------------------------------------------

async def _async_subfinder_scan(domain: str, timeout: int = 600) -> list:
    """Run Subfinder asynchronously and return a deduplicated list of hosts."""
    if not shutil.which("subfinder"):
        logger.error("subfinder is not installed or not in PATH.")
        return []

    cmd = ["subfinder", "-d", domain, "-silent", "-all", "-json"]
    logger.info(f"[*] Running Subfinder on: {domain}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Subfinder timed out for {domain}")
        process.kill()
        await process.communicate()
        return []

    if process.returncode != 0:
        logger.error(f"Subfinder error for {domain}: {stderr.decode().strip()}")
        return []

    subdomains = []
    for line in stdout.decode().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            host = data.get("host")
            if host:
                subdomains.append(host)
        except json.JSONDecodeError:
            # Subfinder sometimes emits plain text lines (e.g. progress info)
            # treat non-JSON lines as raw hostnames if they look like domains
            if "." in line and " " not in line:
                subdomains.append(line)

    subdomains = list(set(filter(None, subdomains)))
    save_output("subfinder", domain, subdomains)
    logger.info(f"[+] Found {len(subdomains)} subdomains for {domain}.")
    return subdomains


def _sync_subfinder(domain: str) -> list:
    """Synchronous wrapper around the async Subfinder scan."""
    try:
        return asyncio.run(_async_subfinder_scan(domain))
    except Exception as e:
        logger.error(f"Subfinder wrapper exception: {e}")
        return []


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery.task(
    name='tasks.scanner_tasks.run_full_scan',
    bind=True,
    soft_time_limit=1800,
    time_limit=1900,
)
def run_full_scan(self, domain: str) -> str:
    """
    Full scan pipeline:
      1. Subdomain enumeration (Subfinder)
      2. Web crawling (Katana + httpx)
      3. JS endpoint discovery (LinkFinder)
      4. Vulnerability scanning (Nuclei)
    """
    logger.info(f"[*] Starting full scan for: {domain}")

    # 1. Subdomain enumeration
    subdomains = _sync_subfinder(domain)
    all_targets = list(set(subdomains + [domain]))
    logger.info(f"[+] {len(all_targets)} total targets to scan.")

    # 2 & 3. Crawl + JS analysis per target
    for target in all_targets:
        try:
            smart_crawler(target)
        except Exception as e:
            logger.error(f"smart_crawler error on {target}: {e}")

        try:
            js_linkfinder(target)
        except Exception as e:
            logger.error(f"js_linkfinder error on {target}: {e}")

    # 4. Vulnerability scanning — use the synchronous wrapper so we don't
    #    call asyncio.run() inside an already-running event loop.
    try:
        run_nuclei_scan_sync(all_targets)
    except Exception as e:
        logger.error(f"Nuclei scan error: {e}")

    logger.info(f"[+] Scan complete for: {domain}")
    return f"Completed scan for {domain}"