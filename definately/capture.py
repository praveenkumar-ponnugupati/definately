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

# Modifier keys fire as no-char events while typing (e.g. Shift before a capital).
# Built defensively because names vary across platforms/pynput versions.
_MODIFIER_NAMES = [
    "shift", "shift_r", "shift_l", "ctrl", "ctrl_r", "ctrl_l",
    "alt", "alt_r", "alt_l", "alt_gr", "cmd", "cmd_r", "cmd_l", "caps_lock",
]
MODIFIER_KEYS = frozenset(
    getattr(keyboard.Key, name) for name in _MODIFIER_NAMES if hasattr(keyboard.Key, name)
)


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

    def feed_text(self, text):
        """Simulate typing `text` through the real key path (Shift emitted for
        capitals, Key.space/backspace/etc. for control chars). Used for testing
        and the demo without OS keyboard permissions."""
        from pynput.keyboard import Key, KeyCode
        specials = {" ": Key.space, "\n": Key.enter, "\t": Key.tab}
        for ch in text:
            if ch in specials:
                self._on_press(specials[ch])
            elif ch == "\b":
                self._on_press(Key.backspace)
            else:
                if ch.isupper():
                    self._on_press(Key.shift)  # real typing emits Shift first
                self._on_press(KeyCode.from_char(ch))

    # ---------- key handling ----------

    def _on_press(self, key):
        if self.paused:
            return
        try:
            # Modifiers (shift/ctrl/alt/cmd/caps) fire as separate no-char events
            # WHILE typing — e.g. Shift before a capital letter. They must NOT
            # end or clear the word in progress.
            if key in MODIFIER_KEYS:
                return
            if key == keyboard.Key.backspace:
                if self.buffer:
                    self.buffer.pop()
                return
            if key in (keyboard.Key.space, keyboard.Key.enter, keyboard.Key.tab):
                self._finalize()
                return
            ch = getattr(key, "char", None)
            if ch is None:
                # genuine cursor movement / focus change (arrows, home, esc, fn keys):
                # we can no longer trust the word position, so drop it.
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
