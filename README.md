# definately

**Your Mac remembers every word you fumble — and every evening, texts you one tiny lesson made only of your own mistakes.**

Built for the Supermemory **localhost:6767** hackathon (July 2026). Everything runs on your machine: capture, memory, and the language model. Nothing about your typing ever leaves your laptop — only the finished digest, sent to *you* over iMessage.

> Yes, the name is misspelled on purpose. *definately* is the typo it exists to cure — a spelling coach that has clearly met itself.

## What it does

You install it and forget it. No window, no chatbot, no dashboard. You just type all day — Mail, Slack, Notes, code — and at 8pm your phone buzzes with one message:

```
definately — today's slip report
✏️ 6 slips today. Top offender: recieve → receive (4th time this month).
🔁 You leaned on "very" 9× today — try genuinely, properly, or wildly.
🎓 Graduated: seperate → separate — 21 days clean. Your fingers finally learned it.
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
- ✅ **Your schedule, your way** — instant alerts on every mistake, and/or a batched digest at set times or every N minutes
- ✅ **Personality** — warm or snarky, five lines max (`tone` in config)
- ✅ **Graduation & relapse** — words you stop misspelling graduate; if they come back, the streak resets
- ✅ **Visible & pausable** — a menu-bar dot shows it's listening; one click to pause

## When do you want to hear about mistakes?

Two independent channels — use either or both:

**1. Instant alerts** — get corrected the moment you slip, like a live coach:
```bash
./venv/bin/python -m definately.cli config instant on
```
Each mistake pops a banner: `recieve → receive (4th time)`. Set `instant_channel`
to `notification` (banner) or `imessage` in `~/.definately/config.json`.

**2. Batched digest** — a summary on your schedule:
```bash
./venv/bin/python -m definately.cli config at 09:00 18:00   # specific times
./venv/bin/python -m definately.cli config every 30         # every 30 minutes
./venv/bin/python -m definately.cli config digest off       # instant-only
./venv/bin/python -m definately.cli config                  # show current settings
```

## Two-way iMessage — chat, learn, and control from your phone

Text definately **anything** about spelling or words and it replies as a coach that
knows *your* history — "why do I keep misspelling receive?", "a trick for ie/ei?",
"a better word than *very*?". The conversation is grounded in your real mistakes
(recalled from Supermemory) and remembers the last few turns. Quality of the
teaching tracks your local model — a bigger `ollama_model` (e.g. `llama3.1:8b`)
gives sharper mnemonics than the tiny default.

It also understands fixed commands for reliable control:

| You text… | It does |
|---|---|
| `help` | lists commands |
| `instant on` / `off` | toggle real-time alerts |
| `every 30` · `at 9:00 18:00` · `digest off` | reschedule the digest |
| `tone snarky` / `kind` | change the voice |
| `pause` · `resume` · `snooze 2h` | stop/start capturing |
| `stats` / `top` | your worst words |
| `more` | fresher synonyms for today's overused word |
| `quiz` | a spelling challenge — reply to answer |

Your preferences persist to `~/.definately/config.json` — they're yours. This
needs **Full Disk Access** (System Settings › Privacy & Security › Full Disk
Access) so definately can read your own incoming messages locally; nothing is
sent anywhere. Test it standalone with `./venv/bin/python -m definately.cli listen`.

## Quick start

```bash
# 1. Supermemory Local (the memory engine)
npx supermemory local
OPENAI_API_KEY=ollama OPENAI_BASE_URL=http://localhost:11434/v1 MODEL=llama3.2:3b supermemory-server

# 2. Ollama (the digest writer)
ollama serve &  ollama pull llama3.2:3b

# 3. definately
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
# set "imessage_to" to your number/Apple ID in ~/.definately/config.json (created on first run)
./venv/bin/python -m definately.app          # menu-bar app
```

Grant **Input Monitoring** and **Accessibility** to your terminal/Python when macOS prompts (needed to observe keystrokes).

## Run it as a background service

Install once and definately starts at every login, stays running, and restarts if it crashes (a macOS LaunchAgent):

```bash
./venv/bin/python -m definately.cli service install     # start now + every login
./venv/bin/python -m definately.cli service status
./venv/bin/python -m definately.cli service stop        # stop until next login
./venv/bin/python -m definately.cli service uninstall   # remove entirely
```

The installer prints the exact Python binary to authorize. Grant it **Accessibility** + **Input Monitoring** (and **Full Disk Access** for two-way iMessage) in System Settings › Privacy & Security — add the binary with the `+` button if it isn't listed. Service logs live in `~/.definately/logs/`.

### Cleaner: build a real `.app`

So macOS permissions attach to **definately.app** (not a raw python binary):

```bash
./venv/bin/pip install py2app
./venv/bin/python setup_app.py py2app -A     # menu-bar app in ./dist/definately.app
```

Grant Accessibility / Input Monitoring / Full Disk Access to **definately.app**, then
`service install` — it auto-detects `dist/definately.app` and runs that under launchd.
(Drop `-A` for a distributable, relocatable bundle.)

### Try it without waiting for 8pm

```bash
./venv/bin/python -m definately.cli doctor   # check the stack
./venv/bin/python -m definately.cli seed     # inject demo slips
./venv/bin/python -m definately.cli digest   # print today's digest
./venv/bin/python -m definately.cli send     # send it to your phone
```

## Roadmap

Reply-to-interact (MORE / spell-quiz), WhatsApp delivery, an iOS keyboard extension for on-phone capture, weekly reports, and per-app writing personas.

## License

MIT
