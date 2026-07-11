"""The evening digest: the product's entire user interface.

Five lines max, written by a local LLM (Ollama), with a deterministic
fallback so the digest always sends even if the model is down.
"""
import httpx

TONES = {
    "kind": "You are a warm, encouraging writing coach with a light sense of humor.",
    "snarky": "You are a dry, witty writing coach. Gentle roasting allowed, never mean.",
}

PROMPT = """%s

Write today's typing digest as a short iMessage (max 5 short lines, a couple of
fitting emoji, no greeting, no sign-off). It must read like a friendly text, not a report.

Use ONLY these facts:
%s

Rules:
- Lead with the most interesting fact.
- If a word was misspelled repeatedly, mention its running total playfully.
- For overused words, suggest 2-3 fresher alternatives (modern, natural English).
- If a word graduated, celebrate it. If one relapsed, mourn it briefly.
- Never invent facts or numbers not listed above."""


_ORDINAL = ["", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th"]


def instant_line(word, correction, count):
    """One-line real-time correction, e.g. 'recieve → receive (4th time)'."""
    nth = _ORDINAL[count] if count < len(_ORDINAL) else "%dth" % count
    tail = " (%s time)" % nth if count > 1 else ""
    return "%s → %s%s" % (word, correction, tail)


def _facts(memory):
    lines = []
    slips = memory.slips_today()
    for s in slips[:5]:
        lines.append("- Misspelled '%s' -> '%s' (%dx today, %dx all-time)"
                     % (s["word"], s["correction"] or "?", s["today"], s["total"]))

    # Supermemory-powered pattern detection: for today's top offender, surface
    # semantically-similar past mistakes (words the local counter can't relate).
    if slips:
        related = memory.related_slips(slips[0]["word"])
        if related:
            words = ", ".join("'%s'" % r["word"] for r in related)
            lines.append("- Pattern: '%s' is the same kind of slip as %s (found by "
                         "semantic memory)" % (slips[0]["word"], words))
    for word, count in memory.overused_today():
        lines.append("- Overused the word '%s' (%dx today)" % (word, count))
    for g in memory.check_graduations():
        lines.append("- GRADUATED: '%s' — %d days clean after %d lifetime slips"
                     % (g["word"], g["clean_days"], g["total"]))
    for r in memory.relapses_today():
        lines.append("- RELAPSED: '%s' — misspelled again after %d days clean"
                     % (r["word"], r["clean_days"]))
    return lines


def build(memory, cfg):
    facts = _facts(memory)
    if not facts:
        return None  # clean day: send nothing (silence is a feature)

    system = TONES.get(cfg["tone"], TONES["kind"])
    prompt = PROMPT % (system, "\n".join(facts))
    try:
        r = httpx.post(
            cfg["ollama_url"].rstrip("/") + "/api/generate",
            json={"model": cfg["ollama_model"], "prompt": prompt, "stream": False},
            timeout=120,
        )
        text = r.json().get("response", "").strip()
        if text:
            return "definately — today's slip report\n" + text
    except Exception:
        pass

    # deterministic fallback: never miss a digest
    return "definately — today's slip report\n" + "\n".join(facts)
