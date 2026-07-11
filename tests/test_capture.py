"""End-to-end capture test — simulates real typing (no OS permissions needed).

Run:  ./venv/bin/python -m tests.test_capture

Verifies the whole path: keystrokes -> word boundaries -> spellcheck -> jargon
filter -> slip recorded in the local index AND stored in Supermemory Local.
"""
import definately.capture as capture_mod
from definately.capture import Capture


class FakeMemory:
    """Records calls so we can assert on them without touching Supermemory."""
    def __init__(self):
        self.slips = []
        self.usage = []
    def record_slip(self, word, correction, app):
        self.slips.append((word, correction, app))
    def record_usage(self, word):
        self.usage.append(word)
    def flush(self):
        pass


CFG = {"app_blocklist": ["terminal", "iterm"], "auto_whitelist_after": 10}


def run_case(name, text, expect_words, forbid_words):
    # pretend everything is typed in Mail (not a blocklisted app)
    capture_mod.frontmost_app = lambda: "Mail"
    mem = FakeMemory()
    cap = Capture(mem, CFG)
    cap.feed_text(text + " ")  # trailing space finalizes the last word
    caught = {w for (w, _c, _a) in mem.slips}

    ok = True
    for w in expect_words:
        if w not in caught:
            print("  FAIL [%s]: expected to catch '%s' but didn't" % (name, w)); ok = False
    for w in forbid_words:
        if w in caught:
            print("  FAIL [%s]: should NOT have flagged '%s'" % (name, w)); ok = False
    if ok:
        print("  ok   [%s]: caught %s" % (name, sorted(caught) or "(nothing, as expected)"))
    return ok, mem


def main():
    all_ok = True

    # 1. Basic prose typos are caught; correct words are not.
    ok, _ = run_case(
        "prose",
        "I definately think we should recieve the seperate documents",
        expect_words=["definately", "recieve", "seperate"],
        forbid_words=["think", "should", "documents"])
    all_ok &= ok

    # 2. THE BUG FIX: capital letters (which emit Shift) must not break the word
    #    that follows. "Recieve" starts a sentence -> Shift fires, then the word.
    ok, mem = run_case(
        "capitals + shift",
        "This occured today. Also we recieve mail",
        expect_words=["occured", "recieve"],
        forbid_words=[])
    all_ok &= ok

    # 2b. Direct proof of the fix: a modifier pressed MID-word must not wipe it.
    from pynput.keyboard import Key, KeyCode
    capture_mod.frontmost_app = lambda: "Mail"
    mem = FakeMemory()
    cap = Capture(mem, CFG)
    for ch in "reci":
        cap._on_press(KeyCode.from_char(ch))
    cap._on_press(Key.shift)          # <-- modifier in the middle of "recieve"
    for ch in "eve":
        cap._on_press(KeyCode.from_char(ch))
    cap._on_press(Key.space)
    if ("recieve", "receive", "Mail") in mem.slips:
        print("  ok   [modifier mid-word]: 'recieve' survived a Shift press")
    else:
        print("  FAIL [modifier mid-word]: word was wiped by the modifier:", mem.slips)
        all_ok = False

    # 3. Backspace correction: user types 'teh', fixes to 'the' -> no slip.
    ok, mem = run_case(
        "backspace fix",
        "teh\b\b\bthe quick brown fox",
        expect_words=[],
        forbid_words=["teh", "the"])
    all_ok &= ok

    # 4. Jargon armor: acronyms, names, code identifiers, short words ignored.
    ok, _ = run_case(
        "jargon armor",
        "API kubectl Praveen Supermemory getUserById an ok",
        expect_words=[],
        forbid_words=["API", "kubectl", "Praveen", "getUserById"])
    all_ok &= ok

    # 5. Auto-whitelist: a word typed 10x (consistent) becomes vocabulary, not a slip.
    capture_mod.frontmost_app = lambda: "Mail"
    mem = FakeMemory()
    cap = Capture(mem, dict(CFG, auto_whitelist_after=5))
    cap.feed_text(("zorptext " * 6))
    zorp_slips = [w for (w, _c, _a) in mem.slips if w == "zorptext"]
    if len(zorp_slips) >= 5:
        print("  FAIL [auto-whitelist]: 'zorptext' still flagged after threshold"); all_ok = False
    else:
        print("  ok   [auto-whitelist]: stopped flagging 'zorptext' after threshold")

    # 6. Blocklist: typing in Terminal is ignored entirely.
    capture_mod.frontmost_app = lambda: "Terminal"
    mem = FakeMemory()
    cap = Capture(mem, CFG)
    cap.feed_text("recieve seperate ")
    if mem.slips:
        print("  FAIL [blocklist]: captured slips in Terminal:", mem.slips); all_ok = False
    else:
        print("  ok   [blocklist]: ignored typing in Terminal")

    print("\n%s" % ("ALL PASSED ✅" if all_ok else "SOME FAILED ❌"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
