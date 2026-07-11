"""sic. configuration — loaded from ~/.sic/config.json, created with defaults on first run."""
import json
import os

SIC_DIR = os.path.expanduser("~/.sic")
CONFIG_PATH = os.path.join(SIC_DIR, "config.json")

DEFAULTS = {
    # Supermemory Local
    "supermemory_url": "http://localhost:6767",
    "container_tag": "sic_slips",
    # Ollama (digest writer)
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2:3b",
    # Delivery: your own phone number or Apple ID email, e.g. "+15551234567"
    "imessage_to": "",
    "digest_time": "20:00",
    "tone": "kind",  # kind | snarky
    # Apps never captured (bundle-id substrings, case-insensitive)
    "app_blocklist": [
        "terminal", "iterm", "1password", "keychain", "bitwarden", "keeper",
    ],
    # Words used this many times (any spelling) are treated as your vocabulary, not typos
    "auto_whitelist_after": 10,
    # A word this many days clean after >=3 slips counts as graduated
    "graduate_after_days": 14,
    # Demo mode: minutes-scale cycle for the demo video (graduation in minutes, digest on demand)
    "demo_mode": False,
}


def load():
    os.makedirs(SIC_DIR, exist_ok=True)
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    else:
        save(cfg)
    return cfg


def save(cfg):
    os.makedirs(SIC_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
