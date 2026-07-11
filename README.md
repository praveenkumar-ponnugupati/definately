# sic.

**Your Mac remembers every word you fumble — and every evening, texts you one tiny lesson made only of your own mistakes.**

Built for the Supermemory **localhost:6767** hackathon (July 2026). Everything runs on your machine: capture, memory, and the language model. Nothing about your typing ever leaves your laptop — only the finished digest, sent to *you* over iMessage.

> `[sic]` — the editor's mark for "the error was in the original." sic. quotes your own typos back to you.

## What it does

You install it and forget it. No window, no chatbot, no dashboard. You just type all day — Mail, Slack, Notes, code — and at 8pm your phone buzzes with one message:

```
sic. — today's slip report
✏️ 6 slips today. Top offender: recieve → receive (4th time this month).
🔁 You leaned on "very" 9× today — try genuinely, properly, or wildly.
🎓 Graduated: definately — 21 days clean. Your fingers finally learned it.
```

## How it works

```
 you type anywhere ─▶ capture daemon ─▶ Supermemory Local (:6767) ─▶ Ollama ─▶ iMessage to you
   (before autocorrect)  spellcheck +      the memory: counts,        writes the   (also lands on
                         jargon filter     history, streaks           digest       iPhone/iPad/Watch)
```

- **Capture** — a keystroke listener rebuilds words and checks them against the Mac's own `NSSpellChecker`. Because it sees keystrokes, it catches typos **before autocorrect hides them** — the mistakes you never knew you made. Password fields use macOS secure input and are invisible to it by design.
- **Memory** — every slip, count, and streak lives in **Supermemory Local**. Semantic recall answers "is this a repeat?", "which words did they beat?", "what do they write about?" — turning a spellchecker into something that *knows you over time*.
- **Digest** — a local LLM (Ollama) writes a five-line, human digest; a deterministic fallback guarantees it always sends.

## Features

- ✅ **Autocorrect-hidden errors** — logs what you *actually* typed
- ✅ **Jargon armor** — ignores names, acronyms, code identifiers, and auto-learns your vocabulary
- ✅ **Personality** — warm or snarky, five lines max (`tone` in config)
- ✅ **Graduation & relapse** — words you stop misspelling graduate; if they come back, the streak resets
- ✅ **Visible & pausable** — a menu-bar dot shows it's listening; one click to pause

## Quick start

```bash
# 1. Supermemory Local (the memory engine)
npx supermemory local
OPENAI_API_KEY=ollama OPENAI_BASE_URL=http://localhost:11434/v1 MODEL=llama3.2:3b supermemory-server

# 2. Ollama (the digest writer)
ollama serve &  ollama pull llama3.2:3b

# 3. sic.
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
# set "imessage_to" to your number/Apple ID in ~/.sic/config.json (created on first run)
./venv/bin/python -m sic.app          # menu-bar app
```

Grant **Input Monitoring** and **Accessibility** to your terminal/Python when macOS prompts (needed to observe keystrokes).

### Try it without waiting for 8pm

```bash
./venv/bin/python -m sic.cli doctor   # check the stack
./venv/bin/python -m sic.cli seed     # inject demo slips
./venv/bin/python -m sic.cli digest   # print today's digest
./venv/bin/python -m sic.cli send     # send it to your phone
```

## Roadmap

Reply-to-interact (MORE / spell-quiz), WhatsApp delivery, an iOS keyboard extension for on-phone capture, weekly reports, and per-app writing personas.

## License

MIT
