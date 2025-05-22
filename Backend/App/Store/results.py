# app/output/results.py
import json
from datetime import datetime

def format_finding(finding, target):
    return {
        "target": target,
        "type": finding.get("vulnerability"),
        "payload": finding.get("payload"),
        "details": {
            "status": finding.get("status"),
            "signature": finding.get("signature", ""),
            "indicators": finding.get("indicators", ""),
            "response_time": finding.get("response_time", ""),
        },
        "timestamp": datetime.utcnow().isoformat()
    }

def process_all(findings, target):
    return [format_finding(f, target) for f in findings]
