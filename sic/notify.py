"""iMessage delivery via the Messages app (AppleScript). Zero servers.

The digest goes to imessage_to (your own number / Apple ID), which lands on
your iPhone, iPad and Watch automatically. Messages falls back to SMS on its
own when a recipient isn't on iMessage.
"""
import subprocess

SCRIPT = '''
on run {targetBuddy, msg}
    tell application "Messages"
        set targetService to 1st account whose service type = iMessage
        set theBuddy to participant targetBuddy of targetService
        send msg to theBuddy
    end tell
end run
'''


def send_imessage(to, text):
    if not to:
        raise ValueError("imessage_to is not set in ~/.sic/config.json")
    subprocess.run(
        ["osascript", "-e", SCRIPT, to, text],
        check=True, capture_output=True, timeout=30,
    )
