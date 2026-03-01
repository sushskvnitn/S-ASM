"""
scanner_tasks.py
Celery task orchestrating the full EASM pipeline.

Pipeline:
  Phase 1 — Recon:    crt.sh + subfinder + puredns + dnsx + asnmap
  Phase 2 — Probe:    naabu (ports) + httpx (live hosts + tech)
  Phase 3 — Crawl:    katana + gau + waybackurls + uro + linkfinder
  Phase 4 — VulnScan: nuclei + nuclei-dast + dalfox + sqlmap
  Phase 5 — Report:   risk score + aggregated JSON
"""

import logging
import os
import sys

# Fix: add Backend directory to sys.path so Celery workers find Modules/Core
_BACKEND_DIR = "/mnt/e/cybersecurity/Projects/S-ASM/Backend"
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from asm_tasks import celery
from Core.Utils import save_output

logger = logging.getLogger(__name__)

# Ensure go/bin in PATH for all child processes
_HOME = os.path.expanduser("~")
_GO_BIN = os.path.join(_HOME, "go", "bin")
if _GO_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _GO_BIN + os.pathsep + os.environ.get("PATH", "")


@celery.task(
    name='tasks.scanner_tasks.run_full_scan',
    bind=True,
    soft_time_limit=5400,
    time_limit=5500,
)
def run_full_scan(self, domain: str) -> dict:
    logger.info(f"[*] Starting EASM scan for: {domain}")

    # Phase 1: Reconnaissance
    logger.info("[*] Phase 1: Reconnaissance")
    try:
        from Modules.recon import run_recon
        recon_result = run_recon(domain)
        subdomains = recon_result.get("subdomains", [])
        ip_ranges = recon_result.get("ip_ranges", [])
        logger.info(f"[+] Recon: {len(subdomains)} live subdomains, {len(ip_ranges)} IP ranges.")
    except Exception as e:
        logger.error(f"[!] Recon phase failed: {e}")
        subdomains = [domain]
        ip_ranges = []

    all_hosts = list(set(subdomains + [domain]))

    # Phase 2: Port Scanning + Live Host Probing
    logger.info("[*] Phase 2: Probing")
    try:
        from Modules.crawler import run_port_scan, probe_with_httpx
        port_map = run_port_scan(all_hosts)
        live_host_data = probe_with_httpx(all_hosts, port_map)
        live_urls = [h.get("url") or h.get("input", "") for h in live_host_data if h]
        live_urls = [u for u in live_urls if u]
        logger.info(f"[+] Probing: {len(live_urls)} live URLs found.")
        save_output("httpx_live", domain, live_host_data)
    except Exception as e:
        logger.error(f"[!] Probe phase failed: {e}")
        live_urls = [f"http://{h}" for h in all_hosts]
        port_map = {}

    # Phase 3: Crawling
    logger.info("[*] Phase 3: Crawling")
    try:
        from Modules.crawler import run_crawl
        crawl_result = run_crawl(domain, live_urls)
        all_urls = crawl_result.get("all_urls", [])
        js_links = crawl_result.get("js_links", [])
        logger.info(
            f"[+] Crawl: {len(all_urls)} URLs "
            f"(gau:{crawl_result.get('gau_count',0)} "
            f"wb:{crawl_result.get('wayback_count',0)} "
            f"katana:{crawl_result.get('katana_count',0)})"
        )
    except Exception as e:
        logger.error(f"[!] Crawl phase failed: {e}")
        all_urls = live_urls
        js_links = []

    # Phase 4: Vulnerability Scanning
    logger.info("[*] Phase 4: Vulnerability Scanning")
    try:
        from Modules.vulnscan import run_vulnscan
        vuln_result = run_vulnscan(domain, all_urls, js_links)
        risk = vuln_result.get("risk", {})
        logger.info(
            f"[+] VulnScan complete: {risk.get('risk_level','?')} risk | "
            f"score={risk.get('score',0)} | "
            f"findings={vuln_result.get('total',0)}"
        )
    except Exception as e:
        logger.error(f"[!] VulnScan phase failed: {e}")
        vuln_result = {"risk": {"risk_level": "ERROR"}, "total": 0}

    # Phase 5: Final Report
    summary = {
        "domain": domain,
        "subdomains_found": len(subdomains),
        "ip_ranges": ip_ranges,
        "live_hosts": len(live_urls),
        "urls_crawled": len(all_urls),
        "js_links": len(js_links),
        "risk": vuln_result.get("risk", {}),
        "total_findings": vuln_result.get("total", 0),
        "findings_breakdown": {
            "nuclei": len(vuln_result.get("nuclei", [])),
            "nuclei_dast": len(vuln_result.get("nuclei_dast", [])),
            "dalfox_xss": len(vuln_result.get("dalfox", [])),
            "sqlmap_sqli": len(vuln_result.get("sqlmap", [])),
        }
    }

    save_output("scan_summary", domain, summary)
    logger.info(f"[+] EASM scan complete for {domain}: {summary}")
    return summary
