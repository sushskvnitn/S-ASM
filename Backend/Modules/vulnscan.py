import json
import asyncio
from typing import List, Dict, Optional
from Core.Utils import run_command, save_output
import os
from datetime import datetime

async def run_single_scan(
    target: str,
    templates: str,
    rate_limit: int = 50,
    notify_config_path: Optional[str] = None,
    severity_filter: str = "info,low,medium,high,critical"
) -> Dict:
    """Run nuclei scan on a single target with severity filtering and notify support."""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    output_json_path = f"nuclei_output_{target}_{timestamp}.json"
    output_txt_path = f"nuclei_output_{target}_{timestamp}.txt"

    cmd = (
        f"echo {target} | nuclei "
        f"-t {templates} "
        f"-json -rl {rate_limit} "
        f"-severity {severity_filter} "
        f"-o {output_txt_path} "
    )

    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stderr:
            print(f"[-] Error scanning {target}: {stderr.decode().strip()}")

        # Save raw JSON output
        findings = []
        for line in stdout.decode().strip().splitlines():
            if line.strip():
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"[-] JSON decode error for {target}: {e}")
        
        # Save to disk
        save_output("nuclei", target, findings)

        # Write raw JSON to file (for later analysis)
        with open(output_json_path, "w") as f:
            json.dump(findings, f, indent=2)

        # Notify if configured and findings exist
        if notify_config_path and findings:
            notify_cmd = (
                f"cat {output_txt_path} | "
                f"notify -pc {notify_config_path} "
                f'-mf "New vuln found on {target}! {{data}}"'
            )
            os.system(notify_cmd)

        return {
            "target": target,
            "findings": findings,
            "json_path": output_json_path,
            "txt_path": output_txt_path,
        }

    except Exception as e:
        print(f"[-] Exception while scanning {target}: {e}")
        return {"target": target, "error": str(e)}


async def run_nuclei_scan(
    targets: List[str],
    templates: str = "~/nuclei-templates/",
    notify_config_path: Optional[str] = None,
    severity_filter: str = "info,low,medium,high,critical"
) -> List[Dict]:
    """Run concurrent nuclei scans on multiple targets with notification and output saving."""
    print(f"[+] Running Nuclei scan on {len(targets)} targets...")

    semaphore = asyncio.Semaphore(10)  # Limit concurrent scans

    async def scan_with_limit(target):
        async with semaphore:
            return await run_single_scan(target, templates, notify_config_path=notify_config_path, severity_filter=severity_filter)

    tasks = [scan_with_limit(target) for target in targets]
    results = await asyncio.gather(*tasks)
    save_output("nuclei", "aggregated", results)
    return results


def run_nuclei_scan_sync(
    targets: List[str],
    templates: str = "~/nuclei-templates/",
    notify_config_path: Optional[str] = None,
    severity_filter: str = "info,low,medium,high,critical"
) -> List[Dict]:
    """Synchronous wrapper for running nuclei scans with severity filter and notify."""
    return asyncio.run(
        run_nuclei_scan(targets, templates, notify_config_path=notify_config_path, severity_filter=severity_filter)
    )
