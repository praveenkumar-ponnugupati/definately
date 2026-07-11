"""Menu-bar app (feature #9): a visible indicator that definately is listening,
a live slip counter, one-click pause, send-now, and quit.
"""
import datetime

import rumps

from . import commands, digest, imessage_in, notify
from .capture import Capture
from .config import load, save
from .memory import Memory


class DefinatelyApp(rumps.App):
    def __init__(self):
        super().__init__("definately", quit_button=None)
        self.cfg = load()
        self.memory = Memory(self.cfg)
        self.capture = Capture(self.memory, self.cfg, on_slip=self._on_slip)

        self._last_instant = 0.0

        self.status_item = rumps.MenuItem("Listening")
        self.pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)
        self.instant_item = rumps.MenuItem("Instant alerts", callback=self.toggle_instant)
        self.instant_item.state = 1 if self.cfg.get("instant_alerts") else 0
        self.schedule_item = rumps.MenuItem(self._schedule_label())  # info only
        self.menu = [
            self.status_item,
            self.schedule_item,
            None,
            rumps.MenuItem("Send digest now", callback=self.send_now),
            self.instant_item,
            self.pause_item,
            None,
            rumps.MenuItem("Quit definately", callback=self.quit_now),
        ]
        self.capture.start()
        self._refresh_title()

        # periodic (every 60s): flush counts, check graduations, check schedule
        rumps.Timer(self._tick, 60).start()
        self._schedule_digest()
        self._init_interactive()  # two-way iMessage control

    # ---------- UI ----------

    def _refresh_title(self):
        dot = "🔴" if self.capture.paused else "🟢"
        self.title = "%s %d" % (dot, self.capture.slips_today)
        self.status_item.title = (
            "Paused" if self.capture.paused
            else "Listening · %d slips today" % self.capture.slips_today)

    def _on_slip(self, word, correction):
        self._refresh_title()
        # (1) INSTANT ALERTS: correct the mistake the moment it happens.
        if self.cfg.get("instant_alerts"):
            import time
            gap = self.cfg.get("instant_min_gap_seconds", 0)
            now = time.time()
            if gap and (now - self._last_instant) < gap:
                return
            self._last_instant = now
            count = self.memory.count_for(word)
            line = digest.instant_line(word, correction, count)
            try:
                notify.deliver(self.cfg.get("instant_channel", "notification"),
                               self.cfg["imessage_to"], "definately", line)
            except Exception:
                pass

    def toggle_pause(self, _):
        paused = self.capture.toggle_pause()
        self.pause_item.title = "Resume" if paused else "Pause"
        self._refresh_title()

    def set_paused(self, value):
        """Programmatic pause/resume (used by iMessage 'pause'/'resume'/'snooze')."""
        if self.capture.paused != value:
            self.capture.toggle_pause()
        self.pause_item.title = "Resume" if value else "Pause"
        self._refresh_title()

    def snooze(self, minutes):
        self.set_paused(True)
        self._snooze_timer = rumps.Timer(self._auto_resume, max(60, minutes * 60))
        self._snooze_timer.start()

    def _auto_resume(self, sender):
        sender.stop()
        self.set_paused(False)

    def toggle_instant(self, sender):
        on = not self.cfg.get("instant_alerts")
        self.cfg["instant_alerts"] = on
        sender.state = 1 if on else 0
        save(self.cfg)  # persist the preference

    def quit_now(self, _):
        self.memory.flush()
        rumps.quit_application()

    # ---------- schedule ----------

    def _schedule_label(self):
        d = self.cfg.get("digest", {})
        mode = d.get("mode", "scheduled")
        if mode == "off":
            return "Digest: off"
        if mode == "interval":
            return "Digest: every %d min" % d.get("every_minutes", 120)
        return "Digest: at %s" % ", ".join(d.get("times", ["20:00"]))

    def _tick(self, _):
        self.memory.flush()
        if self.memory.check_graduations():
            self._refresh_title()
        # scheduled mode: fire when the clock hits one of the configured times
        d = self.cfg.get("digest", {})
        if not self.cfg.get("demo_mode") and d.get("mode", "scheduled") == "scheduled":
            now_hm = datetime.datetime.now().strftime("%H:%M")
            if now_hm in set(d.get("times", ["20:00"])) and now_hm not in self._sent_at:
                self._sent_at.add(now_hm)
                self.send_now(None)
            # reset the per-day guard at midnight
            if now_hm == "00:00":
                self._sent_at = set()

    def _schedule_digest(self):
        """Set up the batched digest per config: interval timer, or demo cadence.
        Scheduled-times mode is handled in _tick (checked each minute)."""
        self._sent_at = set()
        if self.cfg.get("demo_mode"):
            rumps.Timer(lambda _: self.send_now(None), 120).start()
            return
        d = self.cfg.get("digest", {})
        if d.get("mode", "scheduled") == "interval":
            secs = max(60, int(d.get("every_minutes", 120)) * 60)
            rumps.Timer(lambda _: self.send_now(None), secs).start()

    # ---------- interactive iMessage ----------

    def _init_interactive(self):
        """Start listening for replies, so you can control definately by texting back."""
        self._msg_cursor = None
        to = self.cfg.get("imessage_to")
        if not to or not imessage_in.available():
            return  # no number set, or Full Disk Access not granted -> stays one-way
        st = commands._load_state()
        self._msg_cursor = st.get("msg_cursor") or imessage_in.latest_rowid()
        rumps.Timer(self._poll_messages, 8).start()  # check for replies every 8s
        # first-run welcome so the user knows their controls
        if not st.get("welcomed"):
            st["welcomed"] = True
            commands._save_state(st)
            try:
                notify.send_imessage(to, "definately is watching your spelling. "
                                         "Reply 'help' anytime to control me from here.")
            except Exception:
                pass

    def _poll_messages(self, _):
        if self._msg_cursor is None:
            return
        to = self.cfg.get("imessage_to")
        for rowid, text in imessage_in.fetch_incoming(self._msg_cursor, only_from=to):
            self._msg_cursor = rowid
            if not text:
                continue
            reply = commands.handle(text, self.cfg, self.memory, app=self)
            try:
                notify.send_imessage(to, reply)
            except Exception:
                pass
            self.schedule_item.title = self._schedule_label()  # reflect any change
            self.instant_item.state = 1 if self.cfg.get("instant_alerts") else 0
        st = commands._load_state()
        st["msg_cursor"] = self._msg_cursor
        commands._save_state(st)

    # ---------- digest ----------

    def send_now(self, _):
        self.memory.flush()
        text = digest.build(self.memory, self.cfg)
        if not text:
            rumps.notification("definately", "Clean slate", "No slips to report yet.")
            return
        channel = self.cfg.get("digest", {}).get("channel", "imessage")
        try:
            notify.deliver(channel, self.cfg["imessage_to"], "definately — slip report", text)
            rumps.notification("definately", "Digest sent (%s)" % channel, text[:120])
        except Exception as e:
            rumps.notification("definately", "Could not send digest", str(e))


def main():
    DefinatelyApp().run()


if __name__ == "__main__":
    main()
