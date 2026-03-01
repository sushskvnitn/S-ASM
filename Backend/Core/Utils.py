import subprocess
import os
import json
import time
import random


def run_command(cmd: str) -> str:
    """Run a shell command and return its stdout as a string."""
    delay = random.uniform(0.3, 1.8)
    time.sleep(delay)
    try:
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"


def is_domain(input_str: str) -> bool:
    return "." in input_str and not input_str.startswith("http")


def save_output(module: str, target: str, output) -> None:
    """Persist module output to JSON under storage/results/<target>/."""
    # Sanitise target so it's safe as a directory name
    safe_target = target.replace("://", "_").replace("/", "_").replace(":", "_")
    os.makedirs(f"storage/results/{safe_target}", exist_ok=True)
    with open(f"storage/results/{safe_target}/{module}.json", "w") as f:
        json.dump({"output": output}, f, indent=2)