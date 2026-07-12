"""definately configuration — loaded from ~/.definately/config.json, created with defaults on first run."""
import json
import os

DATA_DIR = os.path.expanduser("~/.definately")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULTS = {
    # Supermemory Local
    "supermemory_url": "http://localhost:6767",
    "container_tag": "definately_slips",
    # Ollama (digest writer + conversational tutor). A bigger model gives sharper
    # mnemonics/synonyms; drop to llama3.2:3b if you're tight on RAM.
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.1:8b",
    # Delivery: your own phone number or Apple ID email, e.g. "+15551234567"
    "imessage_to": "",
    "tone": "kind",  # kind | snarky

    # ---- WHEN do you want to hear about mistakes? Two independent channels. ----

    # Interactive chat lives in the CLI (`definately chat`) — fully local, no
    # permissions. iMessage is SEND-ONLY by default (digests/alerts). Set this
    # True only if you want to control definately by replying to texts, which
    # requires Full Disk Access to read your Messages db.
    "imessage_interactive": False,

    # (1) Instant alerts: get corrected the MOMENT you make a mistake.
    "instant_alerts": False,           # True = real-time coaching on every slip
    "instant_channel": "notification", # "notification" (banner) | "imessage"
    "instant_min_gap_seconds": 0,      # throttle: min seconds between instant alerts (0 = none)

    # (2) Batched digest: a summary on YOUR schedule.
    "digest": {
        "mode": "scheduled",           # "scheduled" | "interval" | "off"
        "times": ["20:00"],            # scheduled: one or more HH:MM per day
        "every_minutes": 120,          # interval: send every N minutes while you work
        "channel": "imessage",         # "imessage" | "notification"
    },
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
    os.makedirs(DATA_DIR, exist_ok=True)
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    else:
        save(cfg)
    return cfg


def save(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
