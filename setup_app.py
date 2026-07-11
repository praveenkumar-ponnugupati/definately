"""Build a standalone menu-bar app:  ./venv/bin/python setup_app.py py2app -A

  -A = alias mode (fast dev build that references this venv; not relocatable)
Drop -A for a distributable bundle. The .app gets its own TCC identity, so you
grant Accessibility / Input Monitoring / Full Disk Access to "definately.app"
instead of a raw python binary.
"""
from setuptools import setup

APP = ["launcher.py"]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "definately",
        "CFBundleDisplayName": "definately",
        "CFBundleIdentifier": "com.definately.app",
        "CFBundleVersion": "0.1.0",
        "LSUIElement": True,  # menu-bar only — no Dock icon, no window
        "NSAppleEventsUsageDescription": "definately sends your slip digest via Messages.",
    },
    "packages": ["definately", "rumps", "pynput", "httpx"],
    "includes": ["objc", "Foundation", "AppKit"],
}

setup(
    app=APP,
    name="definately",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
