"""The memory layer: Supermemory Local for semantic memory, plus a small local
stats index for exact counts and streak math (graduation/relapse — feature #7).
"""
import datetime
import json
import os
import threading

import httpx

from .config import DATA_DIR

STATS_PATH = os.path.join(DATA_DIR, "stats.json")
_lock = threading.Lock()


def _today():
    return datetime.date.today().isoformat()


class Memory:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base = cfg["supermemory_url"].rstrip("/")
        self.tag = cfg["container_tag"]
        self.http = httpx.Client(timeout=10)
        self.stats = self._load_stats()

    # ---------- local stats index ----------

    def _load_stats(self):
        if os.path.exists(STATS_PATH):
            with open(STATS_PATH) as f:
                return json.load(f)
        return {"slips": {}, "usage": {}, "graduated": {}, "relapsed": {}}

    def _save_stats(self):
        with _lock:
            with open(STATS_PATH, "w") as f:
                json.dump(self.stats, f, indent=2)

    # ---------- writes ----------

    def record_slip(self, word, correction, app):
        """A misspelling happened. Remember it everywhere."""
        word = word.lower()
        now = datetime.datetime.now().isoformat(timespec="seconds")
        entry = self.stats["slips"].setdefault(
            word, {"count": 0, "correction": correction, "first": now, "days": {}}
        )
        entry["count"] += 1
        entry["last"] = now
        if correction:
            entry["correction"] = correction
        entry["days"][_today()] = entry["days"].get(_today(), 0) + 1

        # relapse check (feature #7): a graduated word has fallen
        if word in self.stats["graduated"]:
            grad = self.stats["graduated"].pop(word)
            self.stats["relapsed"][word] = {
                "graduated_on": grad["on"],
                "relapsed_on": now,
                "clean_days": grad.get("clean_days", 0),
            }
        self._save_stats()

        # semantic memory: full-sentence content so search works naturally
        content = (
            "Typing slip: wrote '%s' instead of '%s' in %s. "
            "This word has been misspelled %d times total."
            % (word, correction or "?", app, entry["count"])
        )
        self._post_memory(content, {
            "kind": "slip", "word": word, "correction": correction or "",
            "app": app, "count": entry["count"], "ts": now,
        })

    def record_usage(self, word):
        """Word-frequency counter for overuse detection. Local only, aggregated."""
        word = word.lower()
        day = self.stats["usage"].setdefault(_today(), {})
        day[word] = day.get(word, 0) + 1
        # persistence happens on flush() to avoid writing on every keystroke

    def flush(self):
        self._save_stats()

    def _post_memory(self, content, metadata):
        try:
            self.http.post(
                self.base + "/v3/documents",
                json={"content": content, "containerTag": self.tag, "metadata": metadata},
            )
        except Exception:
            pass  # never let memory failures break capture

    # ---------- reads (digest fuel) ----------

    def slips_today(self):
        out = []
        for word, e in self.stats["slips"].items():
            n = e["days"].get(_today(), 0)
            if n:
                out.append({"word": word, "correction": e.get("correction"),
                            "today": n, "total": e["count"]})
        return sorted(out, key=lambda s: -s["today"])

    def overused_today(self, top_n=3, min_count=6):
        """Filler words the user leaned on today."""
        fillers = {"very", "really", "just", "actually", "basically", "literally",
                   "good", "nice", "great", "amazing", "awesome", "cool", "stuff",
                   "thing", "things", "totally", "definitely", "honestly"}
        day = self.stats["usage"].get(_today(), {})
        hits = [(w, c) for w, c in day.items() if w in fillers and c >= min_count]
        return sorted(hits, key=lambda x: -x[1])[:top_n]

    def check_graduations(self):
        """Promote words that stayed clean long enough (feature #7)."""
        horizon = self.cfg["graduate_after_days"]
        if self.cfg.get("demo_mode"):
            horizon_seconds = 120  # demo: 2 minutes clean = graduated
        newly = []
        now = datetime.datetime.now()
        for word, e in list(self.stats["slips"].items()):
            if word in self.stats["graduated"] or e["count"] < 3:
                continue
            last = datetime.datetime.fromisoformat(e["last"])
            clean = (now - last)
            ok = clean.total_seconds() >= horizon_seconds if self.cfg.get("demo_mode") \
                else clean.days >= horizon
            if ok:
                days = max(1, clean.days)
                self.stats["graduated"][word] = {
                    "on": now.isoformat(timespec="seconds"), "clean_days": days}
                newly.append({"word": word, "clean_days": days, "total": e["count"]})
                self._post_memory(
                    "Graduated word: '%s' — no misspelling for %d days after %d slips."
                    % (word, days, e["count"]),
                    {"kind": "graduation", "word": word})
        if newly:
            self._save_stats()
        return newly

    def relapses_today(self):
        out = []
        for word, r in self.stats["relapsed"].items():
            if r["relapsed_on"].startswith(_today()):
                out.append({"word": word, "clean_days": r["clean_days"]})
        return out

    def recall(self, query, limit=5):
        """Semantic recall from Supermemory — used for history color in the digest."""
        try:
            r = self.http.post(self.base + "/v3/search",
                               json={"q": query, "containerTag": self.tag, "limit": limit})
            return r.json().get("results", [])
        except Exception:
            return []
