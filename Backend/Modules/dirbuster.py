from Core.Utils import run_command, save_output

def dirbuster(target):
    print(f"[+] Running ffuf on {target}")
    wordlist = "/usr/share/wordlists/dirb/common.txt"
    cmd = f'ffuf -u http://{target}/FUZZ -w {wordlist} -rate 50 -t 20 -mc all -of json'
    output = run_command(cmd)
    save_output("ffuf", target, output)
    return output