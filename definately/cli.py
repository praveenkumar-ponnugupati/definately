"""Command-line entry for testing without the menu bar.

  python -m definately.cli doctor     # check Supermemory + Ollama + config
  python -m definately.cli digest     # build today's digest and print it
  python -m definately.cli send       # build and send via iMessage
  python -m definately.cli seed       # inject demo slips (for the demo video)
  python -m definately.cli simulate "text with tpyos"  # type text through capture -> real memory

Reporting preferences (when/how often you hear about mistakes):
  python -m definately.cli config                 # show current settings
  python -m definately.cli config instant on      # real-time alert on every mistake
  python -m definately.cli config instant off
  python -m definately.cli config every 30        # batched digest every 30 minutes
  python -m definately.cli config at 09:00 18:00  # digest at specific times of day
  python -m definately.cli config digest off      # no batched digest (instant only)
  python -m definately.cli config channel imessage|notification   # where digests go
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


def configure(cfg, args):
    from .config import save
    if not args:
        d = cfg["digest"]
        print("  instant alerts : %s (%s)"
              % ("ON" if cfg["instant_alerts"] else "off", cfg["instant_channel"]))
        if d["mode"] == "off":
            print("  digest         : off")
        elif d["mode"] == "interval":
            print("  digest         : every %d min (%s)" % (d["every_minutes"], d["channel"]))
        else:
            print("  digest         : at %s (%s)" % (", ".join(d["times"]), d["channel"]))
        return
    key = args[0]
    if key == "instant":
        cfg["instant_alerts"] = (args[1].lower() in ("on", "true", "yes"))
        print("  instant alerts -> %s" % ("ON" if cfg["instant_alerts"] else "off"))
    elif key == "every":
        cfg["digest"]["mode"] = "interval"
        cfg["digest"]["every_minutes"] = int(args[1])
        print("  digest -> every %d min" % cfg["digest"]["every_minutes"])
    elif key == "at":
        cfg["digest"]["mode"] = "scheduled"
        cfg["digest"]["times"] = args[1:]
        print("  digest -> at %s" % ", ".join(cfg["digest"]["times"]))
    elif key == "digest" and args[1] == "off":
        cfg["digest"]["mode"] = "off"
        print("  digest -> off (instant only)")
    elif key == "channel":
        cfg["digest"]["channel"] = args[1]
        print("  digest channel -> %s" % args[1])
    else:
        print("  unknown config option. run 'config' with no args to see settings.")
        return
    save(cfg)


def listen(cfg, mem):
    """Standalone two-way loop: read your iMessage replies, act, respond."""
    import time
    from . import commands, imessage_in, notify
    if not cfg.get("imessage_to"):
        print("  set imessage_to in ~/.definately/config.json first"); return
    if not imessage_in.available():
        print("  Can't read Messages. Grant Full Disk Access to your terminal:")
        print("  System Settings > Privacy & Security > Full Disk Access."); return
    cursor = imessage_in.latest_rowid()
    print("  listening for replies from %s  (Ctrl-C to stop)" % cfg["imessage_to"])
    try:
        while True:
            for rowid, text in imessage_in.fetch_incoming(cursor, only_from=cfg["imessage_to"]):
                cursor = rowid
                if not text:
                    continue
                reply = commands.handle(text, cfg, mem)
                print("  <- %r\n  -> %s" % (text, reply.replace(chr(10), " / ")))
                try:
                    notify.send_imessage(cfg["imessage_to"], reply)
                except Exception as e:
                    print("     (send failed: %s)" % e)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n  stopped.")


def watch(cfg, mem):
    """Live capture test: prints each slip as you type it in any app.
    Needs Input Monitoring / Accessibility permission for your terminal."""
    import time
    from .capture import Capture, frontmost_app
    n = [0]
    def on_slip(word, correction):
        n[0] += 1
        print("  #%d  %-16s -> %-16s  [%s]" % (n[0], word, correction, frontmost_app()))
    cap = Capture(mem, cfg, on_slip=on_slip)
    cap.start()
    print("  watching your typing — go type some misspelled words in any app.")
    print("  (Ctrl-C here to stop)\n")
    try:
        while True:
            time.sleep(1)
            mem.flush()
    except KeyboardInterrupt:
        print("\n  caught %d slip(s) this session." % n[0])


def main():
    cfg = load()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "doctor"
    mem = Memory(cfg)
    if cmd == "doctor":
        doctor(cfg)
    elif cmd == "seed":
        seed(mem)
    elif cmd == "simulate":
        from .capture import Capture
        import definately.capture as capmod
        capmod.frontmost_app = lambda: "Notes"  # pretend we're typing in Notes
        text = sys.argv[2] if len(sys.argv) > 2 else \
            "I definately recieve seperate emails that occured yesterday"
        slips = []
        cap = Capture(mem, cfg, on_slip=lambda w, c: slips.append((w, c)))
        cap.feed_text(text + " ")
        mem.flush()
        print("  typed: %s" % text)
        print("  caught %d slip(s): %s" % (len(slips),
              ", ".join("%s->%s" % (w, c) for w, c in slips) or "none"))
    elif cmd == "config":
        configure(cfg, sys.argv[2:])
    elif cmd == "reply":
        from . import commands
        text = " ".join(sys.argv[2:])
        print("  you replied: %r" % text)
        print("  definately  : " + commands.handle(text, cfg, mem).replace("\n", "\n              "))
    elif cmd == "listen":
        listen(cfg, mem)
    elif cmd == "watch":
        watch(cfg, mem)
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
