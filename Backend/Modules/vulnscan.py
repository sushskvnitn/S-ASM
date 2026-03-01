import json
import asyncio
import os
from typing import List, Dict, Optional
from datetime import datetime

from Core.Utils import run_command, save_output


async def _run_single_scan(
    target: str,
    templates: str = "~/nuclei-templates/",
    rate_limit: int = 50,
    notify_config_path: Optional[str] = None,
    severity_filter: str = "info,low,medium,high,critical",
) -> Dict:
    """Run a nuclei scan on a single target asynchronously."""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    # Sanitise target for use in filenames
    safe_target = target.replace("://", "_").replace("/", "_").replace(":", "_")
    output_txt_path = f"nuclei_output_{safe_target}_{timestamp}.txt"
    output_json_path = f"nuclei_output_{safe_target}_{timestamp}.json"

    cmd = (
        f"echo '{target}' | nuclei "
        f"-t {templates} "
        f"-json "
        f"-rl {rate_limit} "
        f"-severity {severity_filter} "
        f"-o {output_txt_path}"
    )

    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if stderr:
            stderr_text = stderr.decode().strip()
            if stderr_text:
                print(f"[-] Nuclei stderr for {target}: {stderr_text}")

        findings = []
        for line in stdout.decode().strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                findings.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # nuclei may emit non-JSON progress lines

        # Persist results
        save_output("nuclei", target, findings)
        with open(output_json_path, "w") as f:
            json.dump(findings, f, indent=2)

        # Optional: send notifications
        if notify_config_path and findings and os.path.isfile(notify_config_path):
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
        print(f"[-] Exception scanning {target}: {e}")
        return {"target": target, "error": str(e)}


async def run_nuclei_scan(
    targets: List[str],
    templates: str = "~/nuclei-templates/",
    notify_config_path: Optional[str] = None,
    severity_filter: str = "info,low,medium,high,critical",
) -> List[Dict]:
    """Run concurrent nuclei scans on multiple targets."""
    print(f"[+] Running Nuclei scan on {len(targets)} target(s)…")

    semaphore = asyncio.Semaphore(10)

    async def _bounded(target):
        async with semaphore:
            return await _run_single_scan(
                target,
                templates=templates,
                notify_config_path=notify_config_path,
                severity_filter=severity_filter,
            )

    tasks = [_bounded(t) for t in targets]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    save_output("nuclei", "aggregated", list(results))
    return list(results)


def run_nuclei_scan_sync(
    targets: List[str],
    templates: str = "~/nuclei-templates/",
    notify_config_path: Optional[str] = None,
    severity_filter: str = "info,low,medium,high,critical",
) -> List[Dict]:
    """
    Synchronous wrapper for nuclei scans.
    Safe to call from Celery workers (no existing event loop).
    """
    return asyncio.run(
        run_nuclei_scan(
            targets,
            templates=templates,
            notify_config_path=notify_config_path,
            severity_filter=severity_filter,
        )
    )