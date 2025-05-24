import asyncio
from Core.Utils import save_output

async def async_js_linkfinder(target, timeout=60):
    print(f"[+] Crawling JS for {target}")
    
    cmd = ["linkfinder", "-i", f"http://{target}", "-o", "cli"]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        if process.returncode != 0:
            error_output = stderr.decode().strip()
            print(f"[!] LinkFinder failed: {error_output}")
            save_output("linkfinder_error", target, error_output)
            return []

        raw_output = stdout.decode()
        links = list(set(
            line.strip() for line in raw_output.splitlines()
            if line.strip().startswith("http")
        ))

        save_output("linkfinder", target, links)
        print(f"[+] Found {len(links)} JS endpoints")
        return links

    except asyncio.TimeoutError:
        print(f"[!] LinkFinder timeout for {target}")
        save_output("linkfinder_timeout", target, "Timeout after 60s")
        return []
    except Exception as e:
        print(f"[!] Exception in LinkFinder: {e}")
        save_output("linkfinder_exception", target, str(e))
        return []

def js_linkfinder(target):
    try:
        return asyncio.run(async_js_linkfinder(target))
    except Exception as e:
        print(f"[!] Error in js_linkfinder wrapper: {e}")
        return []
