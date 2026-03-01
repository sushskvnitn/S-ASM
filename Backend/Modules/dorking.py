import os
import subprocess
from Core.Utils import save_output

# Path to the GoogD0rker script (cloned by environmentsetup.py)
GOOGDORK_PATH = os.path.expanduser("~/tools/GoogD0rker/GoogD0rker.py")


def run_googdork(domain: str) -> list:
    """Run Google dorking using GoogD0rker and return a list of result lines."""
    print(f"[+] Running Google Dorking on: {domain}")

    if not os.path.isfile(GOOGDORK_PATH):
        print(f"[!] GoogD0rker not found at {GOOGDORK_PATH}. Skipping.")
        return []

    try:
        cmd = ["python", GOOGDORK_PATH, "-d", domain]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=120).decode()
        lines = [l for l in output.splitlines() if l.strip()]
        save_output("googdork", domain, lines)
        return lines
    except subprocess.TimeoutExpired:
        print("[!] GoogDork timed out.")
        return []
    except subprocess.CalledProcessError as e:
        print(f"[!] GoogDork failed: {e}")
        return []


def run_dorking_module(domain: str) -> dict:
    """Entry point for the dorking module. Returns a dict of dork results."""
    print(f"[*] Starting Dorking Module for: {domain}")
    g_dorks = run_googdork(domain)
    print(f"[+] Google Dorks found: {len(g_dorks)}")
    return {
        "google_dorks": g_dorks,
    }


# Alias kept for backwards compatibility
googledork = run_dorking_module