"""
recon.py
Phase 1 — Passive + Active Reconnaissance

Covers:
  - Certificate Transparency logs (crt.sh)  — passive, no noise
  - Subfinder                                — passive multi-source
  - PureDNS bruteforce                       — active DNS
  - DNSx validation                          — resolves + filters live hosts
  - ASN / IP range mapping (asnmap)          — finds entire org IP space
"""

import asyncio
import json
import os
import shutil
import requests
from typing import List
from Core.Utils import save_output, run_command

_HOME = os.path.expanduser("~")
_GO_BIN = os.path.join(_HOME, "go", "bin")
if _GO_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _GO_BIN + os.pathsep + os.environ.get("PATH", "")

# Default DNS wordlist for puredns bruteforce
_WORDLIST = "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt"
_DNS_WORDLIST = os.path.join(_HOME, "tools", "subdomains-top1million-5000.txt")


# ---------------------------------------------------------------------------
# crt.sh — Certificate Transparency
# ---------------------------------------------------------------------------

def query_crtsh(domain: str) -> List[str]:
    """Query crt.sh for subdomains via certificate transparency logs."""
    print(f"[+] Querying crt.sh for {domain}")
    try:
        r = requests.get(
            f"https://crt.sh/?q=%.{domain}&output=json",
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 S-ASM-Scanner"}
        )
        if r.status_code != 200:
            print(f"[!] crt.sh returned {r.status_code}")
            return []

        entries = r.json()
        subdomains = set()
        for e in entries:
            name = e.get("name_value", "")
            # name_value can contain newline-separated entries
            for sub in name.splitlines():
                sub = sub.strip().lstrip("*.")
                if sub and domain in sub:
                    subdomains.add(sub)

        result = sorted(subdomains)
        save_output("crtsh", domain, result)
        print(f"[+] crt.sh found {len(result)} subdomains.")
        return result

    except Exception as e:
        print(f"[!] crt.sh query failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Subfinder
# ---------------------------------------------------------------------------

async def _run_subfinder(domain: str, timeout: int = 120) -> List[str]:
    if not shutil.which("subfinder"):
        print("[!] subfinder not found.")
        return []
    print(f"[+] Running subfinder on {domain}")
    cmd = ["subfinder", "-d", domain, "-silent", "-all"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        subs = list(set(
            line.strip() for line in stdout.decode().splitlines()
            if line.strip() and "." in line
        ))
        save_output("subfinder", domain, subs)
        print(f"[+] subfinder found {len(subs)} subdomains.")
        return subs
    except asyncio.TimeoutError:
        print("[!] subfinder timed out.")
        return []
    except Exception as e:
        print(f"[!] subfinder error: {e}")
        return []


# ---------------------------------------------------------------------------
# PureDNS — active DNS bruteforce
# ---------------------------------------------------------------------------

async def _run_puredns(domain: str, wordlist: str = _DNS_WORDLIST, timeout: int = 300) -> List[str]:
    if not shutil.which("puredns"):
        print("[!] puredns not found, skipping DNS bruteforce.")
        return []

    # Use a smaller built-in wordlist fallback if custom one missing
    if not os.path.isfile(wordlist):
        # Try to download a small subdomain wordlist
        wordlist = os.path.join(_HOME, "tools", "subdomains-5000.txt")
        if not os.path.isfile(wordlist):
            os.makedirs(os.path.join(_HOME, "tools"), exist_ok=True)
            try:
                r = requests.get(
                    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt",
                    timeout=30
                )
                with open(wordlist, "w") as f:
                    f.write(r.text)
                print(f"[+] Downloaded DNS wordlist to {wordlist}")
            except Exception as e:
                print(f"[!] Could not download wordlist: {e}")
                return []

    print(f"[+] Running puredns bruteforce on {domain}")
    cmd = ["puredns", "bruteforce", wordlist, domain, "--quiet"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        subs = list(set(
            line.strip() for line in stdout.decode().splitlines()
            if line.strip() and "." in line
        ))
        save_output("puredns", domain, subs)
        print(f"[+] puredns found {len(subs)} subdomains.")
        return subs
    except asyncio.TimeoutError:
        print("[!] puredns timed out.")
        return []
    except Exception as e:
        print(f"[!] puredns error: {e}")
        return []


# ---------------------------------------------------------------------------
# DNSx — validate + filter live hosts
# ---------------------------------------------------------------------------

async def _run_dnsx(hosts: List[str], timeout: int = 120) -> List[str]:
    if not shutil.which("dnsx") or not hosts:
        return hosts  # return as-is if dnsx unavailable

    print(f"[+] Validating {len(hosts)} hosts with dnsx...")
    hosts_input = "\n".join(hosts)
    cmd = ["dnsx", "-silent", "-resp"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(input=hosts_input.encode()), timeout=timeout
        )
        live = list(set(
            line.strip().split()[0] for line in stdout.decode().splitlines()
            if line.strip()
        ))
        print(f"[+] dnsx: {len(live)} live hosts.")
        return live
    except Exception as e:
        print(f"[!] dnsx error: {e}")
        return hosts


# ---------------------------------------------------------------------------
# ASN mapping
# ---------------------------------------------------------------------------

def run_asnmap(domain: str) -> List[str]:
    """Map domain to ASN and return IP ranges owned by the same org."""
    if not shutil.which("asnmap"):
        print("[!] asnmap not found, skipping.")
        return []
    print(f"[+] Running asnmap for {domain}")
    try:
        output = run_command(f"asnmap -d {domain} -silent")
        ranges = [l.strip() for l in output.splitlines() if l.strip()]
        save_output("asnmap", domain, ranges)
        print(f"[+] asnmap found {len(ranges)} IP ranges.")
        return ranges
    except Exception as e:
        print(f"[!] asnmap error: {e}")
        return []


# ---------------------------------------------------------------------------
# Full recon pipeline
# ---------------------------------------------------------------------------

async def _full_recon_async(domain: str) -> dict:
    # Run passive sources concurrently
    crtsh_task = asyncio.get_event_loop().run_in_executor(None, query_crtsh, domain)
    subfinder_task = _run_subfinder(domain)

    crtsh_subs, subfinder_subs = await asyncio.gather(crtsh_task, subfinder_task)

    # Merge passive results
    passive_subs = list(set(crtsh_subs + subfinder_subs))
    print(f"[+] Passive recon total: {len(passive_subs)} unique subdomains.")

    # Active DNS bruteforce
    puredns_subs = await _run_puredns(domain)

    # Merge all
    all_subs = list(set(passive_subs + puredns_subs))
    print(f"[+] Total after bruteforce: {len(all_subs)} unique subdomains.")

    # Validate with dnsx
    live_hosts = await _run_dnsx(all_subs)

    # Save merged results
    save_output("subdomains_all", domain, live_hosts)

    # ASN mapping (sync, run in executor)
    ip_ranges = await asyncio.get_event_loop().run_in_executor(None, run_asnmap, domain)

    return {
        "domain": domain,
        "subdomains": live_hosts,
        "ip_ranges": ip_ranges,
        "total": len(live_hosts),
    }


def run_recon(domain: str) -> dict:
    """Synchronous entry point for the full recon pipeline."""
    try:
        return asyncio.run(_full_recon_async(domain))
    except Exception as e:
        print(f"[!] Recon error: {e}")
        return {"domain": domain, "subdomains": [domain], "ip_ranges": [], "total": 1}