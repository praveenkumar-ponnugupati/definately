"""Read INCOMING iMessages so definately can be controlled by replying.

macOS stores messages in a local SQLite db (~/Library/Messages/chat.db).
Reading it requires **Full Disk Access** for the app/terminal running definately
(System Settings > Privacy & Security > Full Disk Access). Nothing is sent
anywhere — we only read your own message text locally to parse commands.
"""
import os
import sqlite3

CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")


def _decode_attributed_body(blob):
    """Newer macOS stores message text in `attributedBody` (a typedstream blob),
    not the `text` column. Best-effort extraction of the plain string."""
    if not blob:
        return None
    try:
        i = blob.find(b"NSString")
        if i == -1:
            return None
        s = blob[i + len("NSString"):]
        plus = s.find(b"+")
        if plus == -1:
            return None
        s = s[plus + 1:]
        length = s[0]
        if length == 0x81:  # 2-byte little-endian length prefix
            length = int.from_bytes(s[1:3], "little")
            s = s[3:]
        else:
            s = s[1:]
        return s[:length].decode("utf-8", errors="replace").strip() or None
    except Exception:
        return None


def available():
    """Can we read the message db? (Full Disk Access granted + db exists.)"""
    if not os.path.exists(CHAT_DB):
        return False
    try:
        con = sqlite3.connect("file:%s?mode=ro&immutable=1" % CHAT_DB, uri=True, timeout=2)
        con.execute("SELECT ROWID FROM message LIMIT 1")
        con.close()
        return True
    except Exception:
        return False


def latest_rowid():
    """Highest message ROWID right now — start the cursor here so we only react
    to replies that arrive AFTER definately starts."""
    try:
        con = sqlite3.connect("file:%s?mode=ro&immutable=1" % CHAT_DB, uri=True, timeout=2)
        row = con.execute("SELECT MAX(ROWID) FROM message").fetchone()
        con.close()
        return row[0] or 0
    except Exception:
        return 0


def fetch_incoming(since_rowid=0, only_from=None, limit=20):
    """Return [(rowid, text), ...] for inbound messages (is_from_me=0) newer than
    since_rowid. If only_from is set (a phone/email), restrict to that sender."""
    try:
        con = sqlite3.connect("file:%s?mode=ro&immutable=1" % CHAT_DB, uri=True, timeout=2)
        con.row_factory = sqlite3.Row
        q = """
            SELECT m.ROWID as rowid, m.text as text, m.attributedBody as body,
                   h.id as sender
            FROM message m LEFT JOIN handle h ON m.handle_id = h.ROWID
            WHERE m.is_from_me = 0 AND m.ROWID > ?
            ORDER BY m.ROWID ASC LIMIT ?
        """
        rows = con.execute(q, (since_rowid, limit)).fetchall()
        con.close()
    except Exception:
        return []

    out = []
    for r in rows:
        if only_from and r["sender"] and _norm(r["sender"]) != _norm(only_from):
            # still advance the cursor past it, but don't act on it
            out.append((r["rowid"], None))
            continue
        text = r["text"] or _decode_attributed_body(r["body"])
        out.append((r["rowid"], text))
    return out


def _norm(handle):
    """Loose match for phone numbers / emails (ignore +, spaces, dashes)."""
    return "".join(c for c in (handle or "") if c.isalnum()).lower()[-10:]
