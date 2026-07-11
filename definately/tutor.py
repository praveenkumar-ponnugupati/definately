"""Conversational tutor over iMessage.

Any reply that isn't a fixed command becomes a chat turn with a spelling &
vocabulary coach that (a) remembers the conversation and (b) grounds its
answers in YOUR real mistake history, recalled from Supermemory Local.

So iMessage becomes a place to actually learn — "why do I keep misspelling
receive?", "give me a trick for ie/ei", "what's a better word than very?".
"""
import httpx

SYSTEM = (
    "You are definately, a warm, concise spelling and vocabulary coach texting "
    "with someone. Keep replies SHORT (1-3 sentences, SMS-length). Be encouraging "
    "and specific. When they ask about a word they get wrong, give a concrete "
    "memory trick (mnemonic). Use their personal mistake history below to "
    "personalize; never invent mistakes they didn't make."
)

MAX_TURNS = 6  # how much conversation to remember


def _context(memory, question):
    """Pull the user's relevant + top mistakes to ground the tutor."""
    lines = []
    for h in memory.recall(question, limit=4):
        if h.get("correction"):
            lines.append("- %s -> %s (they misspell this)" % (h["word"], h["correction"]))
    top = sorted(memory.stats["slips"].items(), key=lambda kv: -kv[1]["count"])[:5]
    for w, e in top:
        if e.get("correction"):
            line = "- %s -> %s (%dx)" % (w, e["correction"], e["count"])
            if line not in lines:
                lines.append(line)
    return "\n".join(lines) or "(no mistakes recorded yet)"


def chat(text, cfg, memory, history):
    """Return (reply, new_history). history is a list of {'role','content'}."""
    ctx = _context(memory, text)
    convo = ""
    for turn in history[-MAX_TURNS:]:
        who = "User" if turn["role"] == "user" else "definately"
        convo += "%s: %s\n" % (who, turn["content"])

    prompt = (
        "%s\n\nTheir mistake history:\n%s\n\nConversation so far:\n%s"
        "User: %s\ndefinately:" % (SYSTEM, ctx, convo, text)
    )
    try:
        r = httpx.post(
            cfg["ollama_url"].rstrip("/") + "/api/generate",
            json={"model": cfg["ollama_model"], "prompt": prompt, "stream": False},
            timeout=90,
        )
        reply = r.json().get("response", "").strip()
    except Exception:
        reply = ""
    if not reply:
        reply = "I'm here to help with spelling and words — ask me anything, or text 'help' for commands."

    new_history = history[-MAX_TURNS:] + [
        {"role": "user", "content": text},
        {"role": "assistant", "content": reply},
    ]
    return reply, new_history
