import subprocess

def run_command(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, text=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def is_domain(input_str):
    return '.' in input_str and not input_str.startswith("http")

def save_output(module, target, output):
    import os, json
    os.makedirs(f'storage/results/{target}', exist_ok=True)
    with open(f'storage/results/{target}/{module}.json', 'w') as f:
        json.dump({"output": output}, f, indent=2)
