"""Interactive command router: turn an iMessage reply into an action + response.

You control definately entirely from your phone. Reply to any digest with:

  help                    list commands
  instant on | off        real-time alerts on every mistake
  every 30                digest every 30 minutes
  at 9:00 18:00           digest at specific times
  digest off              stop the batched digest
  tone kind | snarky      change the digest voice
  pause | resume          stop / restart capturing
  snooze 2h               pause for a while, then auto-resume
  stats | top             your worst words so far
  more                    more synonyms for today's overused word
  quiz                    a quick spelling challenge (reply to answer)

Preferences persist to ~/.definately/config.json, so they're truly *yours*.
"""
import json
import os
import re

import httpx

from .config import DATA_DIR, save

STATE_PATH = os.path.join(DATA_DIR, "state.json")


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def _save_state(s):
    with open(STATE_PATH, "w") as f:
        json.dump(s, f)


def _synonyms(cfg, word):
    prompt = ("Give 3 fresher, natural single-word alternatives to the overused "
              "word '%s'. Reply with ONLY the words, comma-separated." % word)
    try:
        r = httpx.post(cfg["ollama_url"].rstrip("/") + "/api/generate",
                       json={"model": cfg["ollama_model"], "prompt": prompt, "stream": False},
                       timeout=60)
        return r.json().get("response", "").strip().split("\n")[0]
    except Exception:
        return None


HELP = ("definately — text me anything about spelling or words and we'll chat.\n"
        "Or use quick commands:\n"
        "instant on/off · every 30 · at 9:00 18:00 · digest off\n"
        "tone kind/snarky · pause · resume · snooze 2h\n"
        "stats · more · quiz · help")


def handle(text, cfg, memory, app=None):
    """Return the reply string to send back. Mutates cfg/state as needed.
    `app` (optional) lets pause/resume/snooze reach the live capture object.
    """
    t = (text or "").strip()
    low = t.lower()
    state = _load_state()

    if low in ("help", "commands", "?"):
        return HELP

    if low.startswith("instant"):
        on = "off" not in low
        cfg["instant_alerts"] = on
        save(cfg)
        return "Instant alerts %s." % ("ON — I'll ping you on every slip" if on else "off")

    m = re.match(r"every\s+(\d+)", low)
    if m:
        cfg["digest"]["mode"] = "interval"
        cfg["digest"]["every_minutes"] = int(m.group(1))
        save(cfg)
        return "Got it — digest every %s minutes." % m.group(1)

    if low.startswith("at "):
        times = re.findall(r"\d{1,2}:\d{2}", t)
        if times:
            cfg["digest"]["mode"] = "scheduled"
            cfg["digest"]["times"] = times
            save(cfg)
            return "Digest scheduled at %s." % ", ".join(times)
        return "Try: at 9:00 18:00"

    if low in ("digest off", "mute digest"):
        cfg["digest"]["mode"] = "off"
        save(cfg)
        return "Batched digest off. (Instant alerts unaffected.)"

    if low.startswith("tone"):
        cfg["tone"] = "snarky" if "snark" in low else "kind"
        save(cfg)
        return "Tone set to %s." % cfg["tone"]

    if low in ("pause", "stop"):
        if app:
            app.set_paused(True)
        return "Paused. Reply 'resume' when you want me back."

    if low in ("resume", "start"):
        if app:
            app.set_paused(False)
        return "Back on. Watching your spelling. 👀"

    m = re.match(r"snooze\s+(\d+)\s*([hm]?)", low)
    if m:
        n = int(m.group(1)); unit = m.group(2) or "m"
        mins = n * 60 if unit == "h" else n
        if app:
            app.snooze(mins)
        return "Snoozing %d minutes. I'll auto-resume after." % mins

    if low in ("stats", "top"):
        slips = sorted(memory.stats["slips"].items(),
                       key=lambda kv: -kv[1]["count"])[:5]
        if not slips:
            return "No slips recorded yet. Type something wrong and check back. 😄"
        lines = ["Your top slips:"]
        lines += ["%s → %s (%d×)" % (w, e.get("correction", "?"), e["count"])
                  for w, e in slips]
        return "\n".join(lines)

    if low == "more":
        over = memory.overused_today(top_n=1, min_count=1)
        if not over:
            return "No overused words today — nicely varied writing. 👌"
        word = over[0][0]
        syn = _synonyms(cfg, word) or "(couldn't reach the local model)"
        return "Instead of '%s', try: %s" % (word, syn)

    if low == "quiz":
        slips = sorted(memory.stats["slips"].items(), key=lambda kv: -kv[1]["count"])
        pick = next((e.get("correction") for _w, e in slips if e.get("correction")), None)
        if not pick:
            return "No words to quiz yet. Come back after a few slips."
        state["quiz_answer"] = pick
        _save_state(state)
        scrambled = pick[0] + "___" + pick[-1]
        return ("Spelling quiz! Reply with the correct spelling of a word that "
                "starts '%s' and ends '%s' (you've slipped on it before)."
                % (pick[0], pick[-1])) if len(pick) > 2 else "Reply: %s" % scrambled

    # A quiz answer? (one bare word while a quiz is pending, and not a command.)
    if state.get("quiz_answer") and len(t.split()) == 1:
        target = state.pop("quiz_answer")
        _save_state(state)
        if low == target.lower():
            return "✅ Correct — '%s'. Nice." % target
        return "❌ Not quite. It's '%s'. You'll get it next time." % target

    # Otherwise: talk to the tutor — a real conversation, grounded in your history.
    from . import tutor
    reply, new_history = tutor.chat(t, cfg, memory, state.get("chat_history", []))
    state["chat_history"] = new_history
    _save_state(state)
    return reply
