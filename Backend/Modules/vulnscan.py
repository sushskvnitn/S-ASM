from Core.Utils import run_command, save_output

def run_nuclei_scan(targets):
    print(f"[+] Running Nuclei scan on discovered assets")
    all_vulns = []
    for target in targets:
        cmd = f"echo {target} | nuclei -silent -json"
        result = run_command(cmd)
        all_vulns.append({target: result})
    save_output("nuclei", "aggregated", all_vulns)
    return all_vulns