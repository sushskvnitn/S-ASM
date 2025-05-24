from Core.Utils import run_command, save_output

def subdomain_scan(target):
    print(f"[+] Running subfinder on {target}")
    cmd = f"subfinder -d {target} -silent"
    output = run_command(cmd)
    save_output("subfinder", target, output.splitlines())
    return output.splitlines()




