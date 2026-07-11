"""Command-line entry for testing without the menu bar.

  python -m definately.cli doctor     # check Supermemory + Ollama + config
  python -m definately.cli digest     # build today's digest and print it
  python -m definately.cli send       # build and send via iMessage
  python -m definately.cli seed       # inject demo slips (for the demo video)
"""
import sys

import httpx

from . import digest, notify
from .config import load
from .memory import Memory


def doctor(cfg):
    ok = True
    try:
        httpx.post(cfg["supermemory_url"] + "/v3/search",
                   json={"q": "x", "containerTag": cfg["container_tag"]}, timeout=5)
        print("  supermemory local  ok")
    except Exception as e:
        ok = False; print("  supermemory local  FAIL -", e)
    try:
        httpx.get(cfg["ollama_url"] + "/api/tags", timeout=5)
        print("  ollama             ok")
    except Exception as e:
        print("  ollama             warn -", e, "(digest will use fallback)")
    print("  imessage_to        %s" % (cfg["imessage_to"] or "NOT SET — edit ~/.definately/config.json"))
    return ok


def seed(mem):
    demo = [("recieve", "receive", "Mail"), ("recieve", "receive", "Slack"),
            ("definately", "definitely", "Notes"), ("seperate", "separate", "Mail"),
            ("occured", "occurred", "Slack"), ("recieve", "receive", "Notes")]
    for w, c, a in demo:
        mem.record_slip(w, c, a)
    for _ in range(9):
        mem.record_usage("very")
    for _ in range(7):
        mem.record_usage("just")
    mem.flush()
    print("  seeded %d slips + overuse" % len(demo))


def main():
    cfg = load()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "doctor"
    mem = Memory(cfg)
    if cmd == "doctor":
        doctor(cfg)
    elif cmd == "seed":
        seed(mem)
    elif cmd == "digest":
        print(digest.build(mem, cfg) or "(clean day — nothing to report)")
    elif cmd == "send":
        text = digest.build(mem, cfg)
        if not text:
            print("(clean day — nothing to send)"); return
        notify.send_imessage(cfg["imessage_to"], text)
        print("sent:\n" + text)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
