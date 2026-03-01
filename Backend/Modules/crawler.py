"""
crawler.py
Phase 2 — Probing, Crawling & URL Discovery

Covers:
  - naabu       — port scanning (finds non-standard ports)
  - httpx       — live host probing + tech stack fingerprinting
  - katana      — active crawling of live URLs
  - gau         — historical URLs from Wayback, AlienVault, CommonCrawl
  - waybackurls — Wayback Machine URL archive
  - uro         — smart URL deduplication (removes redundant params)
  - LinkFinder  — JS endpoint extraction
"""

import asyncio
import os
import shutil
import subprocess
import tempfile
from typing import List, Dict
from Core.Utils import run_command, save_output

_HOME = os.path.expanduser("~")
_GO_BIN = os.path.join(_HOME, "go", "bin")
if _GO_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _GO_BIN + os.pathsep + os.environ.get("PATH", "")

# Common ports to scan — covers web, APIs, admin panels, dev servers
COMMON_PORTS = "80,443,8080,8443,8888,9000,9090,3000,4000,4443,5000,7000,7443"


# ---------------------------------------------------------------------------
# Port scanning — naabu
# ---------------------------------------------------------------------------

def run_port_scan(hosts: List[str]) -> Dict[str, List[int]]:
    """Scan common ports across all hosts. Returns {host: [open_ports]}."""
    if not shutil.which("naabu") or not hosts:
        print("[!] naabu not found or no hosts, skipping port scan.")
        return {h: [80, 443] for h in hosts}  # assume web ports as fallback

    print(f"[+] Port scanning {len(hosts)} hosts with naabu...")
    hosts_str = "\n".join(hosts)

    try:
        result = subprocess.run(
            ["naabu", "-p", COMMON_PORTS, "-silent", "-json"],
            input=hosts_str,
            capture_output=True,
            text=True,
            timeout=300,
        )
        port_map: Dict[str, List[int]] = {}
        import json
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                host = data.get("host", "")
                port = data.get("port", 0)
                if host and port:
                    port_map.setdefault(host, []).append(port)
            except Exception:
                pass

        save_output("naabu", "port_scan", port_map)
        total_open = sum(len(v) for v in port_map.values())
        print(f"[+] naabu found {total_open} open ports across {len(port_map)} hosts.")
        return port_map

    except subprocess.TimeoutExpired:
        print("[!] naabu timed out.")
        return {}
    except Exception as e:
        print(f"[!] naabu error: {e}")
        return {}


# ---------------------------------------------------------------------------
# httpx — live probing + tech detection
# ---------------------------------------------------------------------------

def probe_with_httpx(hosts: List[str], port_map: Dict[str, List[int]] = None) -> List[Dict]:
    """
    Probe hosts with httpx. Uses open ports from naabu if available.
    Returns list of {url, status_code, title, tech, ...}
    """
    if not shutil.which("httpx") or not hosts:
        return []

    # Build URL list from hosts + their open ports
    urls = []
    for host in hosts:
        ports = (port_map or {}).get(host, [80, 443])
        for port in ports:
            scheme = "https" if port in (443, 8443, 4443) else "http"
            urls.append(f"{scheme}://{host}:{port}" if port not in (80, 443) else f"{scheme}://{host}")

    print(f"[+] Probing {len(urls)} URLs with httpx...")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(urls))
        tmp = f.name

    try:
        result = subprocess.run(
            ["httpx", "-l", tmp, "-silent", "-json", "-tech-detect", "-title", "-status-code"],
            capture_output=True, text=True, timeout=300,
        )
        import json
        live_hosts = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                live_hosts.append(json.loads(line))
            except Exception:
                pass

        save_output("httpx_probe", "live_hosts", live_hosts)
        print(f"[+] httpx found {len(live_hosts)} live URLs.")
        return live_hosts

    except subprocess.TimeoutExpired:
        print("[!] httpx timed out.")
        return []
    except Exception as e:
        print(f"[!] httpx error: {e}")
        return []
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# Katana — active crawling
# ---------------------------------------------------------------------------

async def _run_katana(url: str, depth: int = 3, timeout: int = 120) -> List[str]:
    if not shutil.which("katana"):
        print("[!] katana not found.")
        return []
    print(f"[+] Katana crawling {url} (depth={depth})")
    cmd = ["katana", "-u", url, "-jc", "-d", str(depth), "-silent", "-kf", "all"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        urls = list(set(
            line.strip() for line in stdout.decode().splitlines() if line.strip()
        ))
        print(f"[+] katana found {len(urls)} URLs from {url}")
        return urls
    except asyncio.TimeoutError:
        print(f"[!] katana timed out for {url}")
        return []
    except Exception as e:
        print(f"[!] katana error: {e}")
        return []


# ---------------------------------------------------------------------------
# GAU — historical URLs
# ---------------------------------------------------------------------------

async def _run_gau(domain: str, timeout: int = 120) -> List[str]:
    if not shutil.which("gau"):
        print("[!] gau not found, skipping.")
        return []
    print(f"[+] gau fetching historical URLs for {domain}")
    cmd = ["gau", "--subs", domain]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        urls = list(set(
            line.strip() for line in stdout.decode().splitlines() if line.strip()
        ))
        print(f"[+] gau found {len(urls)} historical URLs.")
        return urls
    except asyncio.TimeoutError:
        print("[!] gau timed out.")
        return []
    except Exception as e:
        print(f"[!] gau error: {e}")
        return []


# ---------------------------------------------------------------------------
# Waybackurls
# ---------------------------------------------------------------------------

async def _run_waybackurls(domain: str, timeout: int = 90) -> List[str]:
    if not shutil.which("waybackurls"):
        print("[!] waybackurls not found, skipping.")
        return []
    print(f"[+] waybackurls fetching archive for {domain}")
    cmd = ["waybackurls", domain]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        urls = list(set(
            line.strip() for line in stdout.decode().splitlines() if line.strip()
        ))
        print(f"[+] waybackurls found {len(urls)} archived URLs.")
        return urls
    except asyncio.TimeoutError:
        print("[!] waybackurls timed out.")
        return []
    except Exception as e:
        print(f"[!] waybackurls error: {e}")
        return []


# ---------------------------------------------------------------------------
# URO — smart URL deduplication
# ---------------------------------------------------------------------------

def dedup_with_uro(urls: List[str]) -> List[str]:
    """Use uro to remove duplicate/redundant URLs (keeps unique param patterns)."""
    if not shutil.which("uro") or not urls:
        # Fallback: basic dedup
        return list(set(urls))

    print(f"[+] Deduplicating {len(urls)} URLs with uro...")
    try:
        result = subprocess.run(
            ["uro"],
            input="\n".join(urls),
            capture_output=True, text=True, timeout=60,
        )
        deduped = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        print(f"[+] uro reduced to {len(deduped)} unique URLs.")
        return deduped
    except Exception as e:
        print(f"[!] uro error: {e}")
        return list(set(urls))


# ---------------------------------------------------------------------------
# LinkFinder — JS endpoint extraction
# ---------------------------------------------------------------------------

async def _run_linkfinder(url: str, timeout: int = 60) -> List[str]:
    if not shutil.which("linkfinder"):
        print("[!] linkfinder not found.")
        return []
    print(f"[+] LinkFinder scanning {url}")
    cmd = ["linkfinder", "-i", url, "-o", "cli"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        err = stderr.decode()
        if "ModuleNotFoundError" in err or "Error" in err:
            print(f"[!] LinkFinder error: {err.strip()[:100]}")
            return []
        links = list(set(
            line.strip() for line in stdout.decode().splitlines()
            if line.strip().startswith("http")
        ))
        print(f"[+] LinkFinder found {len(links)} JS endpoints.")
        return links
    except asyncio.TimeoutError:
        print(f"[!] LinkFinder timed out for {url}")
        return []
    except Exception as e:
        print(f"[!] LinkFinder error: {e}")
        return []


# ---------------------------------------------------------------------------
# Full crawl pipeline
# ---------------------------------------------------------------------------

async def _full_crawl_async(domain: str, live_host_urls: List[str]) -> dict:
    """
    Run all crawling modules concurrently, merge + dedup results.
    live_host_urls: URLs from httpx probe (already confirmed live)
    """
    # Historical URL discovery (passive, concurrent)
    gau_task = _run_gau(domain)
    wb_task = _run_waybackurls(domain)

    # Active crawl of each live host (limit concurrency to 5)
    sem = asyncio.Semaphore(5)

    async def bounded_katana(url):
        async with sem:
            return await _run_katana(url)

    katana_tasks = [bounded_katana(url) for url in live_host_urls[:20]]  # cap at 20 hosts

    # Run all concurrently
    results = await asyncio.gather(
        gau_task, wb_task, *katana_tasks,
        return_exceptions=True,
    )

    gau_urls = results[0] if not isinstance(results[0], Exception) else []
    wb_urls = results[1] if not isinstance(results[1], Exception) else []
    katana_urls = []
    for r in results[2:]:
        if not isinstance(r, Exception):
            katana_urls.extend(r)

    # Merge all
    all_urls = list(set(gau_urls + wb_urls + katana_urls))
    print(f"[+] Total URLs before dedup: {len(all_urls)}")

    # Smart dedup with uro
    deduped_urls = dedup_with_uro(all_urls)

    # Filter to only URLs belonging to the target domain
    target_urls = [u for u in deduped_urls if domain in u]
    print(f"[+] Target-domain URLs after dedup: {len(target_urls)}")

    # Save
    save_output("katana_httpx", domain, target_urls)
    save_output("gau", domain, gau_urls)
    save_output("waybackurls", domain, wb_urls)

    # JS analysis on live hosts
    lf_tasks = [_run_linkfinder(url) for url in live_host_urls[:10]]
    lf_results = await asyncio.gather(*lf_tasks, return_exceptions=True)
    js_links = []
    for r in lf_results:
        if not isinstance(r, Exception):
            js_links.extend(r)
    js_links = list(set(js_links))
    save_output("linkfinder", domain, js_links)

    return {
        "all_urls": target_urls,
        "js_links": js_links,
        "gau_count": len(gau_urls),
        "wayback_count": len(wb_urls),
        "katana_count": len(katana_urls),
    }


def run_crawl(domain: str, live_host_urls: List[str]) -> dict:
    """Synchronous entry point for the full crawl pipeline."""
    try:
        return asyncio.run(_full_crawl_async(domain, live_host_urls))
    except Exception as e:
        print(f"[!] Crawl error: {e}")
        return {"all_urls": [], "js_links": []}