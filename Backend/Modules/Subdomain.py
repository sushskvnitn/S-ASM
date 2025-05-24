import asyncio
import json
from Core.Utils import save_output

async def async_subfinder_scan(target, timeout=120):
    print(f"[+] Running Subfinder passive scan on: {target}")

    cmd = ["subfinder", "-d", target, "-silent", "-nW", "-timeout", "30"]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        if process.returncode != 0:
            error_output = stderr.decode().strip()
            print(f"[!] Subfinder scan failed: {error_output}")
            save_output("subfinder_error", target, error_output)
            return []

        raw_output = stdout.decode()
        subdomains = list(set(
            line.strip() for line in raw_output.splitlines()
            if line.strip() and '.' in line
        ))

        save_output("subfinder", target, subdomains)
        print(f"[+] Found {len(subdomains)} subdomains.")
        return subdomains

    except asyncio.TimeoutError:
        print(f"[!] Subfinder scan timed out for {target}")
        save_output("subfinder_timeout", target, "Timeout after 120s")
        return []
    except Exception as e:
        print(f"[!] Exception in Subfinder scan: {e}")
        save_output("subfinder_exception", target, str(e))
        return []

def subdomain_scan(target):
    try:
        return asyncio.run(async_subfinder_scan(target))
    except Exception as e:
        print(f"[!] Error in subdomain_scan wrapper: {e}")
        return []
