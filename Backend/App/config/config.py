# app/config/config.py
import json
import os

CONFIG_PATH = os.getenv("ASM_CONFIG_PATH", "config/settings.json")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

config = load_config()
