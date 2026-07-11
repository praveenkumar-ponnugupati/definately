"""The capture daemon: keystrokes -> words -> slips.

Because we watch keystrokes, we see what you ACTUALLY typed — before macOS
autocorrect cleans it up (feature #1). Password fields use secure input,
which keystroke listeners physically cannot observe.
"""
import threading

from AppKit import NSWorkspace  # type: ignore
from pynput import keyboard

from . import spell

SEPARATORS = set(" .,;:!?\n\t\"()[]{}<>/")


def frontmost_app():
    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return str(app.localizedName() or "unknown")
    except Exception:
        return "unknown"


class Capture:
    def __init__(self, memory, cfg, on_slip=None):
        self.memory = memory
        self.cfg = cfg
        self.on_slip = on_slip  # UI callback (menu bar counter)
        self.buffer = []
        self.paused = False
        self.slips_today = 0
        self.words_today = 0
        self._listener = None
        self._word_counts = {}  # for auto-whitelist (feature #2)

    # ---------- lifecycle ----------

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def toggle_pause(self):
        self.paused = not self.paused
        self.buffer = []
        return self.paused

    # ---------- key handling ----------

    def _on_press(self, key):
        if self.paused:
            return
        try:
            if key == keyboard.Key.backspace:
                if self.buffer:
                    self.buffer.pop()
                return
            if key in (keyboard.Key.space, keyboard.Key.enter, keyboard.Key.tab):
                self._finalize()
                return
            ch = getattr(key, "char", None)
            if ch is None:
                # arrows, cmd, etc. — a navigation key ends the word untrusted
                self.buffer = []
                return
            if ch in SEPARATORS:
                self._finalize()
            else:
                self.buffer.append(ch)
                if len(self.buffer) > 60:  # runaway buffer (key-repeat, games)
                    self.buffer = []
        except Exception:
            self.buffer = []

    def _finalize(self):
        word = "".join(self.buffer)
        self.buffer = []
        if not word:
            return
        app = frontmost_app()
        if any(b in app.lower() for b in self.cfg["app_blocklist"]):
            return

        self.words_today += 1
        self.memory.record_usage(word)

        # auto-whitelist: consistent "misspelling" is vocabulary, not a slip
        wl = self._word_counts
        wl[word.lower()] = wl.get(word.lower(), 0) + 1
        if wl[word.lower()] == self.cfg["auto_whitelist_after"]:
            spell.add_to_whitelist(word)
            return

        misspelled, correction = spell.check(word)
        # No correction guess -> almost certainly jargon (kubectl, supermemory),
        # not a real slip. Don't nag about words we can't even suggest a fix for.
        if misspelled and correction:
            self.slips_today += 1
            self.memory.record_slip(word, correction, app)
            if self.on_slip:
                self.on_slip(word, correction)
