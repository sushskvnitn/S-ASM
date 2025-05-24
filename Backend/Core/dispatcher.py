from Core.Utils import is_domain
from Modules.Subdomain import subdomain_scan

def run_tasks(target):
    results = {}

    if is_domain(target):
        results['subdomains'] = subdomain_scan(target)

    # Future: Add dirbuster, nuclei, etc.

    return results
