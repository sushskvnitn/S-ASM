import subprocess
import os
import json
import time
import random

def run_command(cmd):
    delay = random.uniform(0.3, 0.8) # Simulate network delay 
    # between 0.3 and 0.8 seconds
    time.sleep(delay)
    try:
        output = subprocess.check_output(cmd, shell=True, text=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def is_domain(input_str):
    return '.' in input_str and not input_str.startswith("http")

def save_output(module, target, output):
    os.makedirs(f'storage/results/{target}', exist_ok=True)
    with open(f'storage/results/{target}/{module}.json', 'w') as f:
        json.dump({"output": output}, f, indent=2)