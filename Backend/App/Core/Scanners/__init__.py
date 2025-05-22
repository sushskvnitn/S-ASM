# app/core/scanners/__init__.py
from app.core.scanners import dir_traversal, sql_injection, ssrf

SCANNERS = {
    "dir_traversal": dir_traversal.scan,
    "sql_injection": sql_injection.scan,
    "ssrf": ssrf.scan,
}

async def run_all_scans(url, selected_modules):
    all_findings = []
    for module in selected_modules:
        if module in SCANNERS:
            findings = await SCANNERS[module](url)
            all_findings.extend(findings)
    return all_findings
