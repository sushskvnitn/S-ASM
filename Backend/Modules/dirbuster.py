from typing import List, Optional
from Core.Utils import run_command, save_output


def smart_crawler(target: str) -> Optional[List[str]]:
    """
    Crawl a target URL with Katana, then validate discovered URLs with httpx.

    Args:
        target: hostname or URL to crawl (without scheme).

    Returns:
        List of live URLs, or None if crawling fails entirely.
    """
    try:
        print(f"[+] Running katana on {target}")
        # -jc: parse JS files for links  -d 2: crawl depth 2
        cmd = f"katana -u http://{target} -jc -d 2 -silent"
        output = run_command(cmd)

        if not output:
            print(f"[-] No output from katana for {target}")
            return None

        links = [l.strip() for l in output.splitlines() if l.strip()]
        if not links:
            print(f"[-] No links found for {target}")
            return []

        print(f"[+] Validating {len(links)} URLs with httpx…")
        live_urls = []

        for link in links:
            try:
                # httpx -sc prints "<url> [<status_code>]", e.g. "http://... [200]"
                validation = run_command(f'echo "{link}" | httpx -silent -sc')
                if validation:
                    # Any non-empty httpx output means the URL responded
                    live_urls.append(link)
            except Exception as e:
                print(f"[-] Error validating {link}: {e}")
                continue

        if live_urls:
            save_output("katana_httpx", target, live_urls)
        return live_urls

    except Exception as e:
        print(f"[-] Error crawling {target}: {e}")
        return None