from Core.Utils import run_command, save_output

def js_linkfinder(target):
    print(f"[+] Crawling JS for {target}")
    cmd = f"linkfinder -i http://{target} -o cli"
    output = run_command(cmd)
    links = output.splitlines()
    save_output("linkfinder", target, links)
    return links