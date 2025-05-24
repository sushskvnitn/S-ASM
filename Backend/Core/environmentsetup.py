import subprocess
import shutil
import os
import time

# Define tools and their install methods
TOOLS = {
    "subfinder": {
        "check": "subfinder",
        "install": "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    },
    "katana": {
        "check": "katana",
        "install": "go install github.com/projectdiscovery/katana/cmd/katana@latest"
    },
    "linkfinder": {
        "check": "linkfinder",
        "install": (
            "mkdir -p ~/tools && "
            "git clone https://github.com/GerbenJavado/LinkFinder.git ~/tools/LinkFinder && "
            "cd ~/tools/LinkFinder && "
            "pip install -r requirements.txt && "
            "chmod +x linkfinder.py && "
            "sudo ln -sf $(pwd)/linkfinder.py /usr/local/bin/linkfinder"
        )
    },
    "nuclei": {
        "check": "nuclei",
        "install": "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
    },
    "redis-server": {
        "check": "redis-server",
        "install": "sudo apt-get update && sudo apt-get install -y redis-server"
    },
    'GoogDork': {
        "check": "googdork",
        "install": (
            "mkdir -p ~/tools && "
            "git clone https://github.com/iamj0ker/GoogD0rker.git ~/tools/GoogD0rker && "
            "cd ~/tools/GoogD0rker && "
            "pip install -r requirements.txt && "
            "chmod +x googdork.py && "
            "sudo ln -sf $(pwd)/googdork.py /usr/local/bin/googdork"
        )
    }
}


def check_tool(tool_name):
    return shutil.which(TOOLS[tool_name]["check"]) is not None


def install_tool(tool_name):
    print(f"[-] {tool_name} not found. Installing...")
    install_cmd = TOOLS[tool_name]["install"]
    try:
        subprocess.run(install_cmd, shell=True, check=True, executable="/bin/bash")
        print(f"[+] {tool_name} installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to install {tool_name}: {e}. Please install it manually.")


def export_go_bin_to_path():
    gopath = os.popen("go env GOPATH").read().strip()
    gobin = os.path.join(gopath, "bin")
    os.environ["PATH"] += os.pathsep + gobin


def ensure_redis_running():
    print("[*] Checking if Redis server is running...")
    try:
        subprocess.check_output(["redis-cli", "ping"])
        print("[+] Redis server is running.")
    except subprocess.CalledProcessError:
        print("[!] Redis server not running. Attempting to start it...")
        try:
            subprocess.Popen(["redis-server"])
            time.sleep(3)
            subprocess.check_output(["redis-cli", "ping"])
            print("[+] Redis server started successfully.")
        except Exception as e:
            print(f"[!] Failed to start Redis server: {e}")


def setup_environment():
    print("==== Environment Setup Started ====")
    export_go_bin_to_path()
    for tool in TOOLS:
        if not check_tool(tool):
            install_tool(tool)
        else:
            print(f"[+] {tool} is already installed.")
    ensure_redis_running()
    print("==== Environment Setup Complete ====")

