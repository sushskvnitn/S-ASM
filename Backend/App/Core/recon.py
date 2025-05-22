# app/core/recon.py
import requests
import socket
import concurrent.futures

def get_subdomains(domain):
    print(f"[+] Fetching subdomains for {domain}")
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    try:
        response = requests.get(url, timeout=10)
        subdomains = set()
        for entry in response.json():
            name = entry["name_value"].lower()
            subdomains.update(name.split("\n"))
        return list(subdomains)
    except Exception as e:
        print(f"[-] Subdomain fetch failed: {e}")
        return []

def scan_ports(host, ports=[80, 443, 8080, 8443]):
    print(f"[+] Scanning ports on {host}")
    open_ports = []

    def check_port(port):
        try:
            with socket.create_connection((host, port), timeout=2):
                return port
        except:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_port, port) for port in ports]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                open_ports.append(result)

    return open_ports
