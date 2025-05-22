# app/main.py
import asyncio
import argparse

from Core.Scanners import dir_traversal, sql_injection, ssrf
from Store import results, storage

async def run_scanners(target):
    print(f"🚀 Scanning: {target}")

    all_findings = []

    print("🔍 Running Directory Traversal Scanner...")
    dt_findings = await dir_traversal.scan(target)
    all_findings.extend(dt_findings)

    print("🔍 Running SQL Injection Scanner...")
    sqli_findings = await sql_injection.scan(target)
    all_findings.extend(sqli_findings)

    print("🔍 Running SSRF Scanner...")
    ssrf_findings = await ssrf.scan(target)
    all_findings.extend(ssrf_findings)

    return all_findings

async def main():
    parser = argparse.ArgumentParser(description="ASM Tool Scanner")
    parser.add_argument("--url", required=True, help="Target URL to scan (e.g. https://example.com/page)")
    args = parser.parse_args()

    target = args.url
    findings = await run_scanners(target)

    if not findings:
        print("✅ No vulnerabilities found.")
        return

    formatted = results.process_all(findings, target)
    report_path = storage.save_results(formatted, target)

    print(f"\n✅ Scan complete. Report saved at: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())
