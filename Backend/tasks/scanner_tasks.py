from celery_worker import celery
from Modules.Subdomain import subdomain_scan
from Modules.dirbuster import dirbuster
from Modules.js_crawler import js_linkfinder
from Modules.vulnscan import run_nuclei_scan
from Core.Utils import save_output

@celery.task(name='tasks.scanner_tasks.run_full_scan')
def run_full_scan(domain):
    print(f"[*] Starting scan for {domain}")

    subdomains = subdomain_scan(domain)
    all_targets = list(set(subdomains + [domain]))
    print(f"[+] {len(all_targets)} targets to scan")

    for target in all_targets:
        dirbuster(target)
        js_linkfinder(target)

    run_nuclei_scan(all_targets)

    return f"Completed scan for {domain}"