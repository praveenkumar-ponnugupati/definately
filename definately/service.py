"""Run definately as a background service (macOS LaunchAgent).

A LaunchAgent starts definately at login, keeps it running, and restarts it if
it crashes — so the menu-bar app is just always there.

  definately service install     # start now + every login
  definately service uninstall   # stop + remove
  definately service status
  definately service start | stop
"""
import os
import subprocess
import sys

LABEL = "com.definately.agent"
PLIST_PATH = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
LOG_DIR = os.path.expanduser("~/.definately/logs")

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>            <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>definately.app</string>
    </array>
    <key>WorkingDirectory</key>  <string>{workdir}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>    <string>{workdir}</string>
        <key>PATH</key>          <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>         <true/>
    <key>KeepAlive</key>        <true/>
    <key>ThrottleInterval</key>  <integer>10</integer>
    <key>StandardOutPath</key>   <string>{log}/agent.out.log</string>
    <key>StandardErrorPath</key> <string>{log}/agent.err.log</string>
    <key>ProcessType</key>       <string>Interactive</string>
</dict>
</plist>
"""


def _domain_target():
    return "gui/%d" % os.getuid()


def _write_plist():
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    workdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plist = PLIST_TEMPLATE.format(
        label=LABEL, python=sys.executable, workdir=workdir, log=LOG_DIR)
    with open(PLIST_PATH, "w") as f:
        f.write(plist)
    return workdir


def _launchctl(*args, check=False):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, check=check)


def install():
    workdir = _write_plist()
    # modern bootstrap, fall back to legacy load
    _launchctl("bootout", _domain_target(), PLIST_PATH)  # clear any stale copy
    r = _launchctl("bootstrap", _domain_target(), PLIST_PATH)
    if r.returncode != 0:
        r = _launchctl("load", "-w", PLIST_PATH)
    ok = r.returncode == 0
    print("  %s definately service (%s)" % ("installed —" if ok else "install FAILED:",
                                            PLIST_PATH))
    if not ok:
        print("  " + (r.stderr.strip() or "unknown launchctl error"))
    else:
        print("  running now, and will auto-start at every login.")
        print("  logs: %s" % LOG_DIR)
        print("  NOTE: grant Input Monitoring + Accessibility (and Full Disk Access for")
        print("        interactive iMessage) to: %s" % sys.executable)
    return ok


def uninstall():
    _launchctl("bootout", _domain_target(), PLIST_PATH)
    _launchctl("unload", PLIST_PATH)
    if os.path.exists(PLIST_PATH):
        os.remove(PLIST_PATH)
    print("  definately service stopped and removed.")


def start():
    _launchctl("kickstart", "-k", "%s/%s" % (_domain_target(), LABEL))
    print("  started.")


def stop():
    _launchctl("bootout", _domain_target(), PLIST_PATH)
    print("  stopped (will restart at next login unless uninstalled).")


def status():
    if not os.path.exists(PLIST_PATH):
        print("  not installed. run: definately service install")
        return
    r = _launchctl("print", "%s/%s" % (_domain_target(), LABEL))
    if r.returncode != 0:
        print("  installed but not loaded. run: definately service start")
        return
    state = pid = "?"
    for line in r.stdout.splitlines():
        s = line.strip()
        if s.startswith("state ="):
            state = s.split("=", 1)[1].strip()
        if s.startswith("pid ="):
            pid = s.split("=", 1)[1].strip()
    print("  definately service: state=%s pid=%s" % (state, pid))
    print("  logs: %s" % LOG_DIR)


def main(args):
    cmd = args[0] if args else "status"
    {"install": install, "uninstall": uninstall, "start": start,
     "stop": stop, "status": status}.get(cmd, status)()
