import subprocess
import shutil
import os
import time

# ---------------------------------------------------------------------------
# PATH — Go bin must come first so go-installed tools beat apt versions
# ---------------------------------------------------------------------------
_HOME = os.path.expanduser("~")
_GO_BIN = os.path.join(_HOME, "go", "bin")


def _ensure_go_bin_in_path():
    current = os.environ.get("PATH", "")
    if _GO_BIN not in current.split(os.pathsep):
        os.environ["PATH"] = _GO_BIN + os.pathsep + current


_ensure_go_bin_in_path()

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
TOOLS = {
    # ── Recon ──────────────────────────────────────────────────────────────
    "subfinder": {
        "check": "subfinder",
        "via": "apt",
        "install": "sudo apt-get install -y subfinder",
    },
    "dnsx": {
        "check": "dnsx",
        "via": "go",
        "install": "go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
    },
    "puredns": {
        "check": "puredns",
        "via": "go",
        "install": "go install github.com/d3mondev/puredns/v2@latest",
    },
    "asnmap": {
        "check": "asnmap",
        "via": "go",
        "install": "go install github.com/projectdiscovery/asnmap/cmd/asnmap@latest",
    },
    # ── Probing ────────────────────────────────────────────────────────────
    "httpx": {
        "check": "httpx",
        "via": "go",
        "install": "go install github.com/projectdiscovery/httpx/cmd/httpx@latest",
        "verify_flag": "-version",          # must contain "projectdiscovery"
    },
    "naabu": {
        "check": "naabu",
        "via": "go",
        "install": "go install github.com/projectdiscovery/naabu/cmd/naabu@latest",
    },
    # ── Crawling ───────────────────────────────────────────────────────────
    "katana": {
        "check": "katana",
        "via": "go",
        "install": "go install github.com/projectdiscovery/katana/cmd/katana@latest",
    },
    "gau": {
        "check": "gau",
        "via": "go",
        "install": "go install github.com/lc/gau/v2/cmd/gau@latest",
    },
    "waybackurls": {
        "check": "waybackurls",
        "via": "go",
        "install": "go install github.com/tomnomnom/waybackurls@latest",
    },
    "uro": {
        "check": "uro",
        "via": "pip",
        "install": "pip install uro --break-system-packages",
    },
    # ── JS Analysis ────────────────────────────────────────────────────────
    "linkfinder": {
        "check": "linkfinder",
        "via": "git",
        "install": (
            "mkdir -p ~/tools && "
            "git clone https://github.com/GerbenJavado/LinkFinder.git ~/tools/LinkFinder && "
            "cd ~/tools/LinkFinder && "
            "pip install -r requirements.txt --break-system-packages && "
            "chmod +x linkfinder.py && "
            "sudo ln -sf $(pwd)/linkfinder.py /usr/local/bin/linkfinder"
        ),
    },
    # ── Fuzzing ────────────────────────────────────────────────────────────
    "ffuf": {
        "check": "ffuf",
        "via": "go",
        "install": "go install github.com/ffuf/ffuf/v2@latest",
    },
    # ── Vuln Scanning ──────────────────────────────────────────────────────
    "nuclei": {
        "check": "nuclei",
        "via": "apt",
        "install": "sudo apt-get install -y nuclei",
    },
    "dalfox": {
        "check": "dalfox",
        "via": "go",
        "install": "go install github.com/hahwul/dalfox/v2@latest",
    },
    # ── Infrastructure ─────────────────────────────────────────────────────
    "redis-server": {
        "check": "redis-server",
        "via": "apt",
        "install": "sudo apt-get install -y redis-server",
    },
}

# Python packages needed in the venv / system
PIP_PACKAGES = [
    "jsbeautifier",
    "requests",
    "flask",
    "celery",
    "redis",
    "uro",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, shell=True, check=check, executable="/bin/bash",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def _check_httpx_is_pd() -> bool:
    path = shutil.which("httpx")
    if not path:
        return False
    try:
        r = _run("httpx -version", check=False)
        return "projectdiscovery" in (r.stdout + r.stderr).lower()
    except Exception:
        return False


def check_tool(name: str) -> bool:
    if name == "httpx":
        return _check_httpx_is_pd()
    return shutil.which(TOOLS[name]["check"]) is not None


def install_tool(name: str) -> bool:
    print(f"[-] {name} not found. Installing...")
    try:
        _run(TOOLS[name]["install"], check=True)
        _ensure_go_bin_in_path()
        print(f"[+] {name} installed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to install {name}: {e.stderr.strip() or e}")
        return False


def install_pip_packages() -> None:
    for pkg in PIP_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            print(f"[-] pip package '{pkg}' missing. Installing...")
            try:
                _run(f"pip install {pkg} --break-system-packages", check=True)
                print(f"[+] {pkg} installed.")
            except subprocess.CalledProcessError:
                print(f"[!] Failed to install pip package: {pkg}")


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

def ensure_redis_running() -> bool:
    print("[*] Checking Redis...")
    try:
        r = _run("redis-cli ping", check=False)
        if "PONG" in r.stdout:
            print("[+] Redis is running.")
            return True
    except Exception:
        pass
    print("[!] Starting Redis...")
    try:
        subprocess.Popen(
            ["sudo", "service", "redis-server", "start"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        r = _run("redis-cli ping", check=False)
        if "PONG" in r.stdout:
            print("[+] Redis started.")
            return True
        print("[!] Redis still not responding.")
        return False
    except Exception as e:
        print(f"[!] Could not start Redis: {e}")
        return False


# ---------------------------------------------------------------------------
# Nuclei templates
# ---------------------------------------------------------------------------

def ensure_nuclei_templates() -> bool:
    templates_path = os.path.join(_HOME, "nuclei-templates")
    if os.path.isdir(templates_path):
        print("[+] nuclei-templates present.")
        return True
    print("[-] Updating nuclei templates...")
    try:
        _run("nuclei -update-templates", check=True)
        print("[+] nuclei-templates updated.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to update nuclei templates: {e.stderr.strip()}")
        return False


# ---------------------------------------------------------------------------
# Wordlists for ffuf
# ---------------------------------------------------------------------------

def ensure_wordlists() -> None:
    wl = "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt"
    if os.path.isfile(wl):
        print("[+] Wordlists present.")
        return
    print("[-] Installing wordlists...")
    try:
        _run("sudo apt-get install -y wordlists dirbuster", check=False)
        _run("sudo gunzip /usr/share/wordlists/rockyou.txt.gz 2>/dev/null || true", check=False)
        print("[+] Wordlists installed.")
    except Exception as e:
        print(f"[!] Wordlist install failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def setup_environment() -> dict:
    print("==== Environment Setup Started ====")
    _ensure_go_bin_in_path()

    results = {}
    failed = []

    for name in TOOLS:
        if check_tool(name):
            print(f"[+] {name} ready.")
            results[name] = "ok"
        else:
            ok = install_tool(name)
            results[name] = "installed" if ok else "failed"
            if not ok:
                failed.append(name)

    install_pip_packages()

    redis_ok = ensure_redis_running()
    results["redis_running"] = "ok" if redis_ok else "failed"
    if not redis_ok:
        failed.append("redis_running")

    nuclei_ok = ensure_nuclei_templates()
    results["nuclei_templates"] = "ok" if nuclei_ok else "failed"
    if not nuclei_ok:
        failed.append("nuclei_templates")

    ensure_wordlists()

    print("==== Environment Setup Complete ====")
    if failed:
        print(f"[!] Needs attention: {', '.join(failed)}")
    else:
        print("[+] All components ready.")

    return {"status": "done", "results": results, "failed": failed}