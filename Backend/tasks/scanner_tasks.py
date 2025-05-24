from celery_worker import celery
from Modules.dirbuster import smart_crawler
from Modules.js_crawler import js_linkfinder
from Modules.vulnscan import run_nuclei_scan
from Core.Utils import save_output

import asyncio
import json
import logging
import shutil  # Ensure shutil is imported here for checking command availability

logger = logging.getLogger(__name__)


async def async_subfinder_scan(domain: str, timeout: int = 600) -> list:
    """Run Subfinder scan asynchronously with JSON output and timeout."""
    cmd = ["subfinder", "-d", domain, "-silent", "-all", "-json"]
    logger.info(f"[*] Running Subfinder scan on: {domain}")
    logger.debug(f"Subfinder command: {' '.join(cmd)}")
    # Ensure the command is executable
    if not shutil.which("subfinder"):
        logger.error("Subfinder is not installed or not in PATH.")
        return []

    if not shutil.which("subfinder"):
        logger.error("Subfinder is not installed or not in PATH.")
        return []
    
    process = await asyncio.create_subprocess_exec(  # Create the subprocess
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    logger.debug(f"Subfinder process started with PID: {process.pid}")
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Subfinder scan timed out for {domain}")
        process.kill()
        await process.communicate()
        return []

    if process.returncode != 0:
        logger.error(f"Subfinder error for {domain}: {stderr.decode().strip()}")
        return []

    subdomains = []
    for line in stdout.decode().splitlines():
        try:
            data = json.loads(line)
            subdomains.append(data.get("host"))
        except json.JSONDecodeError:
            logger.warning(f"[!] Failed to parse JSON from subfinder: {line}")
            continue

    subdomains = list(set(filter(None, subdomains)))
    save_output("subfinder", domain, subdomains)
    logger.info(f"[+] Found {len(subdomains)} subdomains.")
    return subdomains


def sync_subfinder_wrapper(domain: str) -> list:
    """Synchronous wrapper for async Subfinder scan."""
    try:
        return asyncio.run(async_subfinder_scan(domain))
    except Exception as e:
        logger.error(f"Subfinder exception: {e}")
        return []


@celery.task(name='tasks.scanner_tasks.run_full_scan', soft_time_limit=1800, time_limit=1900)
def run_full_scan(domain):
    logger.info(f"[*] Starting scan for {domain}")

    subdomains = sync_subfinder_wrapper(domain)
    all_targets = list(set(subdomains + [domain]))
    logger.info(f"[+] {len(all_targets)} targets to scan")

    for target in all_targets:
        smart_crawler(target)
        js_linkfinder(target)


    run_nuclei_scan(all_targets)

    

    return f"Completed scan for {domain}"
