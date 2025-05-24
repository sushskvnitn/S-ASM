from Core.Utils import run_command, save_output

def subdomain_scan(target):
    print(f"[+] Running Amass on {target}")
    cmd = f"amass enum -passive -d {target}"
    output = run_command(cmd)
    lines = output.splitlines()
    save_output("amass", target, lines)
    return lines