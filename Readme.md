# Attack Surface Management tool

Architecture diagram :

```
asm-backend/
├── app/
│   ├── config/                         # ← Configuration Layer
│   │   ├── __init__.py
│   │   ├── config.py                   # Configuration Manager
│   │   ├── ratelimiter.py              # Rate Limiter
│   │   └── headers.py                  # Header Rotation
│
│   ├── core/                           # ← Core Components
│   │   ├── __init__.py
│   │   ├── recon.py                    # Reconnaissance Engine
│   │   ├── validator.py                # Vulnerability Validator
│   │   └── scanners/                   # Scanner Module
│   │       ├── __init__.py
│   │       ├── dir_traversal.py
│   │       ├── sql_injection.py
│   │       ├── ssrf.py
│   │       └── ... (other checks)
│
│   ├── stealth/                        # ← Stealth Features
│   │   ├── __init__.py
│   │   ├── traffic.py                  # Traffic Shaping
│   │   ├── randomizer.py               # Request Randomization
│   │   └── fingerprint.py              # Fingerprint Management
│
│   ├── output/                         # ← Output Handling
│   │   ├── __init__.py
│   │   ├── results.py                  # Results Processor
│   │   └── storage.py                  # Storage System (DB, JSON, etc.)
│
│   └── main.py                         # FastAPI Entry Point or CLI Logic
│
├── config/                             # Settings & Config Files
│   └── settings.json
│
├── requirements.txt                    # Python dependencies
├── Dockerfile                          # (Optional) Docker support
├── README.md                           # Project overview

```
