"""
vulnscan.py
Phase 3 — Vulnerability Scanning

Covers:
  - Nuclei (CVE templates + misconfig + DAST injection templates)
  - Dalfox (XSS detection on parameter URLs)
  - SQLMap (SQLi detection on parameter URLs)
  - Parameter URL extraction (filters URLs with query params)
  - Severity scoring + result aggregation
"""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

from Core.Utils import save_output

_HOME = os.path.expanduser("~")
_GO_BIN = os.path.join(_HOME, "go", "bin")
if _GO_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _GO_BIN + os.pathsep + os.environ.get("PATH", "")

_NUCLEI_BIN = shutil.which("nuclei") or "nuclei"
_DEFAULT_TEMPLATES = os.path.expanduser("~/nuclei-templates/")

# Severity weights for scoring
SEVERITY_SCORE = {
    "critical": 10,
    "high": 7,
    "medium": 4,
    "low": 2,
    "info": 0,
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def extract_param_urls(urls: List[str]) -> List[str]:
    """Return only URLs that have query parameters — best candidates for injection."""
    return [u for u in urls if "?" in u and "=" in u]


def deduplicate_urls(urls: List[str]) -> List[str]:
    """Deduplicate URLs, keeping one representative per unique param pattern."""
    seen_patterns = set()
    result = []
    for url in urls:
        try:
            parsed = urlparse(url)
            params = frozenset(parse_qs(parsed.query).keys())
            pattern = (parsed.netloc, parsed.path, params)
            if pattern not in seen_patterns:
                seen_patterns.add(pattern)
                result.append(url)
        except Exception:
            result.append(url)
    return result


# ---------------------------------------------------------------------------
# Nuclei
# ---------------------------------------------------------------------------

async def _run_nuclei(targets: List[str], templates: str = _DEFAULT_TEMPLATES,
                      severity: str = "low,medium,high,critical",
                      rate_limit: int = 50, timeout: int = 1800) -> List[Dict]:
    if not targets:
        return []

    templates = os.path.expanduser(templates)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(deduplicate_urls(targets)))
        targets_file = f.name

    output_json = f"/tmp/nuclei_output_{timestamp}.json"

    cmd = (
        f"{_NUCLEI_BIN} -l {targets_file} "
        f"-t {templates} "
        f"-rl {rate_limit} "
        f"-severity {severity} "
        f"-json-export {output_json} "
        f"-silent"
    )

    print(f"[+] Nuclei scanning {len(targets)} targets (severity: {severity})...")

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        # Filter noisy stderr
        noisy = ("[INF]", "Could not unmarshal", "WRN")
        for line in stderr.decode().splitlines():
            if line and not any(n in line for n in noisy):
                print(f"[-] nuclei: {line}")

        findings = []
        if os.path.isfile(output_json):
            with open(output_json) as f:
                raw = f.read().strip()
            if raw:
                try:
                    findings = json.loads(raw)
                    if not isinstance(findings, list):
                        findings = [findings]
                except json.JSONDecodeError:
                    for line in raw.splitlines():
                        try:
                            findings.append(json.loads(line.strip()))
                        except Exception:
                            pass

        print(f"[+] Nuclei found {len(findings)} findings.")
        return findings

    except asyncio.TimeoutError:
        print("[!] Nuclei timed out.")
        return []
    except Exception as e:
        print(f"[!] Nuclei error: {e}")
        return []
    finally:
        for f in [targets_file, output_json]:
            try:
                os.unlink(f)
            except Exception:
                pass


async def _run_nuclei_dast(param_urls: List[str], timeout: int = 900) -> List[Dict]:
    """Run nuclei DAST templates specifically on parameter URLs."""
    if not param_urls:
        return []
    dast_templates = os.path.join(os.path.expanduser("~/nuclei-templates"), "dast")
    if not os.path.isdir(dast_templates):
        print("[!] DAST templates not found, skipping DAST scan.")
        return []
    print(f"[+] Running Nuclei DAST on {len(param_urls)} parameter URLs...")
    return await _run_nuclei(
        param_urls,
        templates=dast_templates,
        severity="low,medium,high,critical",
        rate_limit=20,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Dalfox — XSS scanner
# ---------------------------------------------------------------------------

async def _run_dalfox(param_urls: List[str], timeout: int = 600) -> List[Dict]:
    if not shutil.which("dalfox") or not param_urls:
        if not shutil.which("dalfox"):
            print("[!] dalfox not found, skipping XSS scan.")
        return []

    print(f"[+] Dalfox XSS scanning {len(param_urls)} URLs...")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(param_urls[:100]))  # cap at 100 to avoid very long scans
        tmp = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "dalfox", "file", tmp, "--skip-bav", "--no-spinner", "--format", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        findings = []
        for line in stdout.decode().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                findings.append(json.loads(line))
            except json.JSONDecodeError:
                # Dalfox also prints plain-text vuln lines
                if "[POC]" in line or "[V]" in line:
                    findings.append({"type": "xss", "url": line, "severity": "high"})

        print(f"[+] Dalfox found {len(findings)} XSS findings.")
        return findings

    except asyncio.TimeoutError:
        print("[!] Dalfox timed out.")
        return []
    except Exception as e:
        print(f"[!] Dalfox error: {e}")
        return []
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# SQLMap — SQL injection
# ---------------------------------------------------------------------------

def _run_sqlmap(param_urls: List[str], timeout: int = 600) -> List[Dict]:
    """Run sqlmap on parameter URLs. Runs sync (sqlmap doesn't support async)."""
    if not shutil.which("sqlmap") or not param_urls:
        if not shutil.which("sqlmap"):
            print("[!] sqlmap not found, skipping SQLi scan.")
        return []

    print(f"[+] SQLMap scanning {len(param_urls)} parameter URLs...")
    findings = []

    # Cap to 20 URLs to keep scan time reasonable
    for url in param_urls[:20]:
        try:
            result = subprocess.run(
                [
                    "sqlmap", "-u", url,
                    "--batch",           # no interactive prompts
                    "--level=2",
                    "--risk=2",
                    "--output-dir=/tmp/sqlmap_output",
                    "--forms",
                    "--crawl=1",
                    "--quiet",
                ],
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout + result.stderr
            # Check if sqlmap found injectable params
            if "is vulnerable" in output or "Parameter:" in output:
                findings.append({
                    "type": "sqli",
                    "url": url,
                    "severity": "high",
                    "details": [l for l in output.splitlines() if "Parameter" in l or "vulnerable" in l],
                })
        except subprocess.TimeoutExpired:
            print(f"[!] sqlmap timed out for {url}")
        except Exception as e:
            print(f"[!] sqlmap error for {url}: {e}")

    print(f"[+] SQLMap found {len(findings)} SQLi findings.")
    return findings


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def calculate_risk_score(all_findings: List[Dict]) -> Dict:
    """Aggregate findings into a risk score and severity breakdown."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    score = 0

    for f in all_findings:
        sev = (
            f.get("info", {}).get("severity", "")
            or f.get("severity", "info")
        ).lower()
        if sev in counts:
            counts[sev] += 1
            score += SEVERITY_SCORE.get(sev, 0)

    if score >= 50:
        risk = "CRITICAL"
    elif score >= 20:
        risk = "HIGH"
    elif score >= 10:
        risk = "MEDIUM"
    elif score > 0:
        risk = "LOW"
    else:
        risk = "INFORMATIONAL"

    return {
        "risk_level": risk,
        "score": score,
        "breakdown": counts,
        "total_findings": len(all_findings),
    }


# ---------------------------------------------------------------------------
# Full vuln scan pipeline
# ---------------------------------------------------------------------------

async def _full_vulnscan_async(
    domain: str,
    all_urls: List[str],
    js_links: List[str],
) -> dict:
    """
    Run all vuln scanners concurrently where possible.
    all_urls: from crawler (katana + gau + wayback)
    js_links: from linkfinder
    """
    # Combine and deduplicate
    combined_urls = deduplicate_urls(list(set(all_urls + js_links + [f"http://{domain}"])))
    param_urls = extract_param_urls(combined_urls)

    print(f"[+] Total URLs for scanning: {len(combined_urls)}")
    print(f"[+] Parameter URLs for injection testing: {len(param_urls)}")

    # Run nuclei (full templates) + nuclei DAST + dalfox concurrently
    nuclei_task = _run_nuclei(combined_urls)
    nuclei_dast_task = _run_nuclei_dast(param_urls)
    dalfox_task = _run_dalfox(param_urls)

    nuclei_findings, dast_findings, dalfox_findings = await asyncio.gather(
        nuclei_task, nuclei_dast_task, dalfox_task,
        return_exceptions=True,
    )

    # Handle exceptions from gather
    nuclei_findings = nuclei_findings if not isinstance(nuclei_findings, Exception) else []
    dast_findings = dast_findings if not isinstance(dast_findings, Exception) else []
    dalfox_findings = dalfox_findings if not isinstance(dalfox_findings, Exception) else []

    # SQLMap runs sync in a thread to not block the event loop
    loop = asyncio.get_event_loop()
    sqlmap_findings = await loop.run_in_executor(None, _run_sqlmap, param_urls)

    # Aggregate all findings
    all_findings = nuclei_findings + dast_findings + dalfox_findings + sqlmap_findings

    # Score
    risk_summary = calculate_risk_score(all_findings)

    # Save per scanner
    save_output("nuclei", domain, nuclei_findings)
    save_output("nuclei_dast", domain, dast_findings)
    save_output("dalfox", domain, dalfox_findings)
    save_output("sqlmap", domain, sqlmap_findings)
    save_output("vuln_summary", domain, {
        "risk": risk_summary,
        "all_findings": all_findings,
    })

    print(f"[+] Scan complete. Risk: {risk_summary['risk_level']} | Score: {risk_summary['score']} | Findings: {risk_summary['total_findings']}")

    return {
        "risk": risk_summary,
        "nuclei": nuclei_findings,
        "nuclei_dast": dast_findings,
        "dalfox": dalfox_findings,
        "sqlmap": sqlmap_findings,
        "total": len(all_findings),
    }


def run_vulnscan(domain: str, all_urls: List[str], js_links: List[str] = None) -> dict:
    """Synchronous entry point safe to call from Celery workers."""
    try:
        return asyncio.run(_full_vulnscan_async(domain, all_urls, js_links or []))
    except Exception as e:
        print(f"[!] Vulnscan error: {e}")
        return {"risk": {"risk_level": "ERROR"}, "total": 0}