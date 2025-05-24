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

| Module                       | Status     | Tools / Techniques                         |
| ---------------------------- | ---------- | ------------------------------------------ |
| Directory Discovery          | ✅ Planned | ffuf, dirsearch, JS rendering (Playwright) |
| Vulnerability Scanning       | ✅ Planned | Nuclei, OWASP ZAP, Burp                    |
| Credential Leaks             | ✅ Planned | Pastebin, GitHub, gitleaks                 |
| Hardcoded Secrets            | ✅ Planned | Regex + ML                                 |
| Subdomain Enumeration        | ✅ Planned | Amass, Subfinder                           |
| JS Analysis                  | ✅ Planned | LinkFinder, Custom Regex                   |
| Backup File Discovery        | ✅ Planned | Path bruteforce                            |
| Header Misconfig Detection   | ✅ Planned | SecurityHeaders.io like logic              |
| Screenshot Recon             | ✅ Planned | Headless Chrome, aquatone                  |
| Asset Classification         | ✅ Planned | AI/ML or keyword tagging                   |
| WAF Fingerprinting           | ✅ Planned | WAFW00f, custom detection logic            |
| API & Swagger Analysis       | ✅ Planned | Swagger Parser, BOLA testing               |
| CI/CD Integration            | ✅ Planned | GitHub/GitLab CI hooks                     |
| Real-Time Alerting/Dashboard | ✅ Planned | WebSocket/Kafka + React/Next.js dashboard  |
| WebAssembly & Mobile Recon   | ✅ Planned | WASM decompilers, APK endpoint enumeration |
| Privacy Violation Detection  | ✅ Planned | NLP or regex for personal data             |
| Ai - Ml integration          | ✅ Planned | Gen Ai                                     |
