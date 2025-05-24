import os
import subprocess
from Core.Utils import save_output

GOOGDORK_PATH = os.path.join("Tools", "GoogD0rker", "GoogD0rker.py")
GITDORKER_PATH = os.path.join("Tools", "GitDorker", "GitDorker.py")
GITHUB_TOKEN_FILE = os.path.join("config", "github_token.txt")
DORK_LIST_FILE = os.path.join("config", "github_dorks.txt")


def run_googdork(domain: str) -> list:
    """Run Google dorking using GoogDork."""
    print(f"[+] Running Google Dorking on: {domain}")
    try:
        cmd = ["python", GOOGDORK_PATH, "-d", domain]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
        lines = output.splitlines()
        save_output("googdork", domain, lines)
        return lines
    except subprocess.CalledProcessError as e:
        print(f"[!] GoogDork failed: {e}")
        return []


def run_gitdorker(domain: str) -> list:
    """Run GitHub dorking using GitDorker."""
    print(f"[+] Running GitHub Dorking on: {domain}")
    output_dir = os.path.join("outputs", "gitdorker", domain)
    os.makedirs(output_dir, exist_ok=True)

    try:
        cmd = [
            "python", GITDORKER_PATH,
            "-tf", GITHUB_TOKEN_FILE,
            "-q", domain,
            "-d", DORK_LIST_FILE,
            "-o", output_dir
        ]
        subprocess.check_output(cmd, stderr=subprocess.DEVNULL)

        # Read all results from output files
        results = []
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    results.extend(f.read().splitlines())

        save_output("gitdorker", domain, results)
        return results
    except subprocess.CalledProcessError as e:
        print(f"[!] GitDorker failed: {e}")
        return []


def run_dorking_module(domain: str):
    print(f"[*] Starting Dorking Module for: {domain}")
    g_dorks = run_googdork(domain)
    gh_dorks = run_gitdorker(domain)
    print(f"[+] Google Dorks found: {len(g_dorks)}")
    print(f"[+] GitHub Dorks found: {len(gh_dorks)}")
    return {
        "google_dorks": g_dorks,
        "github_dorks": gh_dorks
    }