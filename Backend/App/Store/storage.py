# app/output/storage.py
import os
import json
from datetime import datetime

RESULT_DIR = "scan_results"
os.makedirs(RESULT_DIR, exist_ok=True)

def save_results(results, target):
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    file_name = f"{RESULT_DIR}/{target.replace('://', '_').replace('/', '_')}_{timestamp}.json"

    with open(file_name, "w") as f:
        json.dump(results, f, indent=4)

    return file_name
