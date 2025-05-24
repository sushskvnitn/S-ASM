from typing import List, Optional
from Core.Utils import run_command, save_output

def smart_crawler(target: str) -> Optional[List[str]]:
    """
    Crawls a target URL using katana and validates found URLs with httpx.
    
    Args:
        target (str): The target URL to crawl
        
    Returns:
        Optional[List[str]]: List of valid URLs or None if crawling fails
    """
    try:
        print(f"[+] Running katana on {target}")
        cmd = f"katana -u http://{target} -jc -d 2"
        output = run_command(cmd)
        if not output:
            print(f"[-] No output received from katana for {target}")
            return None
            
        links = output.splitlines()
        if not links:
            print(f"[-] No links found for {target}")
            return []
            
        print(f"[+] Validating with httpx...")
        live_urls = []
        for link in links:
            try:
                validation = run_command(f"echo {link} | httpx -silent -status-code")
                if validation and validation.strip().isdigit():
                    live_urls.append(link)
            except Exception as e:
                print(f"[-] Error validating {link}: {str(e)}")
                continue
                
        if live_urls:
            save_output("katana_httpx", target, live_urls)
            return live_urls
        return []
        
    except Exception as e:
        print(f"[-] Error crawling {target}: {str(e)}")
        return None