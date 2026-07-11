"""Spellchecking + the "is this actually a slip?" filter.

Uses the Mac's own NSSpellChecker, so definately agrees with the system dictionary
and respects words the user has taught macOS ("Learn Spelling").
"""
import json
import os
import re

from AppKit import NSSpellChecker  # type: ignore

from .config import DATA_DIR

WHITELIST_PATH = os.path.join(DATA_DIR, "whitelist.json")

_checker = NSSpellChecker.sharedSpellChecker()

_WORD_RE = re.compile(r"^[a-zA-Z']+$")


def _load_whitelist():
    if os.path.exists(WHITELIST_PATH):
        with open(WHITELIST_PATH) as f:
            return set(json.load(f))
    return set()


_whitelist = _load_whitelist()


def add_to_whitelist(word):
    _whitelist.add(word.lower())
    with open(WHITELIST_PATH, "w") as f:
        json.dump(sorted(_whitelist), f, indent=2)


def is_checkable(word):
    """Filter out things that are not English prose words: jargon armor (feature #2)."""
    if len(word) < 4:
        return False
    if not _WORD_RE.match(word):
        return False  # digits, URLs, paths, emoji
    if word.isupper():
        return False  # acronyms: API, ASAP
    if word[0].isupper():
        return False  # names: Praveen, Supermemory (prose typos are rarely capitalized)
    if any(c.isupper() for c in word[1:]):
        return False  # camelCase identifiers
    if word.lower() in _whitelist:
        return False
    return True


def check(word):
    """Return (misspelled: bool, correction: str or None)."""
    if not is_checkable(word):
        return False, None
    rng = _checker.checkSpellingOfString_startingAt_(word, 0)
    if rng.length == 0:
        return False, None
    if _checker.hasLearnedWord_(word):
        return False, None  # user taught macOS this word
    guesses = _checker.guessesForWordRange_inString_language_inSpellDocumentWithTag_(
        (0, len(word)), word, "en", 0
    )
    correction = str(guesses[0]) if guesses else None
    return True, correction
