"""Menu-bar app (feature #9): a visible indicator that sic. is listening,
a live slip counter, one-click pause, send-now, and quit.
"""
import datetime
import threading

import rumps

from . import digest, notify
from .capture import Capture
from .config import load, save
from .memory import Memory


class SicApp(rumps.App):
    def __init__(self):
        super().__init__("sic.", quit_button=None)
        self.cfg = load()
        self.memory = Memory(self.cfg)
        self.capture = Capture(self.memory, self.cfg, on_slip=self._on_slip)

        self.status_item = rumps.MenuItem("Listening")
        self.pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)
        self.menu = [
            self.status_item,
            None,
            rumps.MenuItem("Send digest now", callback=self.send_now),
            self.pause_item,
            None,
            rumps.MenuItem("Quit sic.", callback=self.quit_now),
        ]
        self.capture.start()
        self._refresh_title()

        # periodic: flush usage counts + check for graduations
        rumps.Timer(self._tick, 60).start()
        self._schedule_digest()

    # ---------- UI ----------

    def _refresh_title(self):
        dot = "🔴" if self.capture.paused else "🟢"
        self.title = "%s %d" % (dot, self.capture.slips_today)
        self.status_item.title = (
            "Paused" if self.capture.paused
            else "Listening · %d slips today" % self.capture.slips_today)

    def _on_slip(self, word, correction):
        self._refresh_title()

    def toggle_pause(self, _):
        paused = self.capture.toggle_pause()
        self.pause_item.title = "Resume" if paused else "Pause"
        self._refresh_title()

    def quit_now(self, _):
        self.memory.flush()
        rumps.quit_application()

    # ---------- timers ----------

    def _tick(self, _):
        self.memory.flush()
        newly = self.memory.check_graduations()
        if newly:
            self._refresh_title()

    def _schedule_digest(self):
        """Fire the digest at cfg['digest_time'] each day (or every 2 min in demo mode)."""
        if self.cfg.get("demo_mode"):
            rumps.Timer(lambda _: self.send_now(None), 120).start()
            return

        def loop():
            import time
            while True:
                now = datetime.datetime.now()
                hh, mm = map(int, self.cfg["digest_time"].split(":"))
                target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if target <= now:
                    target += datetime.timedelta(days=1)
                time.sleep(max(1, (target - now).total_seconds()))
                self.send_now(None)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    # ---------- digest ----------

    def send_now(self, _):
        self.memory.flush()
        text = digest.build(self.memory, self.cfg)
        if not text:
            rumps.notification("sic.", "Clean slate", "No slips to report today.")
            return
        try:
            notify.send_imessage(self.cfg["imessage_to"], text)
            rumps.notification("sic.", "Digest sent", text[:120])
        except Exception as e:
            rumps.notification("sic.", "Could not send iMessage", str(e))


def main():
    SicApp().run()


if __name__ == "__main__":
    main()
