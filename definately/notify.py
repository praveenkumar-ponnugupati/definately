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
        raise ValueError("imessage_to is not set in ~/.definately/config.json")
    subprocess.run(
        ["osascript", "-e", SCRIPT, to, text],
        check=True, capture_output=True, timeout=30,
    )


NOTIF_SCRIPT = '''
on run {theTitle, theBody}
    display notification theBody with title theTitle
end run
'''


def send_notification(title, text):
    """A macOS banner — instant, local, doesn't touch your phone."""
    subprocess.run(
        ["osascript", "-e", NOTIF_SCRIPT, title, text],
        check=True, capture_output=True, timeout=15,
    )


def deliver(channel, imessage_to, title, text):
    """Route a message to the chosen channel."""
    if channel == "imessage":
        send_imessage(imessage_to, text)
    else:
        send_notification(title, text)
