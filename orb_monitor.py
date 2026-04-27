#!/usr/bin/env python3
"""
Claude Desktop Usage Orb Monitor

Reads the "Current session" usage % from the Claude desktop app via
screencapture + Vision OCR and updates an Electric Imp orb every minute:
  Green (#00FF00) = 0%   Red (#FF0000) = 100%

Requirements:
  - Claude desktop app running with Settings → Usage page visible
  - macOS (uses screencapture + Swift/Vision for OCR)
  - pip install requests

Setup (one-time compile of the OCR binary):
  swiftc get_usage.swift -o get_usage
"""

import os
import re
import sys
import time
import shutil
import tempfile
import subprocess
import requests
from datetime import datetime

ORB_URL = "https://agent.electricimp.com/WSsuAkQ6L4g5"
UPDATE_INTERVAL = 60  # seconds
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_BINARY = os.path.join(SCRIPT_DIR, "get_usage")
CAPTURE_FILE = tempfile.mktemp(suffix=".png")


def ensure_ocr_binary():
    """Compile get_usage.swift if the binary doesn't exist yet."""
    if os.path.exists(OCR_BINARY):
        return
    swift_src = os.path.join(SCRIPT_DIR, "get_usage.swift")
    if not os.path.exists(swift_src):
        sys.exit(f"Missing {swift_src} — clone the full repo.")
    print("Compiling OCR binary (one-time)...")
    result = subprocess.run(
        ["swiftc", swift_src, "-o", OCR_BINARY],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.exit(f"Swift compile failed:\n{result.stderr}")
    print("Compiled OK.\n")


def get_claude_window_id():
    """Return the CGWindowID of the frontmost Claude window."""
    code = """
import CoreGraphics
let wins = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as! [[CFString: Any]]
for w in wins {
    if let owner = w[kCGWindowOwnerName] as? String, owner == "Claude",
       let layer = w[kCGWindowLayer] as? Int, layer == 0,
       let wid = w[kCGWindowNumber] as? CGWindowID {
        print(wid)
        break
    }
}
"""
    result = subprocess.run(["swift", "-e", code], capture_output=True, text=True)
    text = result.stdout.strip()
    return int(text) if text.isdigit() else None


def get_session_pct() -> float:
    """Screenshot the Claude window, OCR it, return usage as 0.0–1.0."""
    window_id = get_claude_window_id()
    if window_id is None:
        raise RuntimeError("Claude window not found — is the app running?")

    # Capture the window (screencapture handles the modern macOS APIs)
    subprocess.run(
        ["screencapture", "-l", str(window_id), "-x", "-o", CAPTURE_FILE],
        check=True, capture_output=True
    )

    result = subprocess.run(
        [OCR_BINARY, CAPTURE_FILE],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return int(result.stdout.strip()) / 100.0


def pct_to_color(pct: float) -> str:
    """Green (0%) → Yellow (50%) → Red (100%)."""
    pct = max(0.0, min(1.0, pct))
    if pct <= 0.5:
        r = int(pct * 2 * 255)
        g = 255
    else:
        r = 255
        g = int((1.0 - (pct - 0.5) * 2) * 255)
    return f"#{r:02X}{g:02X}00"


def update_orb(color: str) -> int:
    resp = requests.post(
        ORB_URL,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"program": "Demo", "color": color},
        timeout=10,
    )
    return resp.status_code


def main():
    ensure_ocr_binary()

    print("Orb monitor started")
    print(f"  Source        : Claude desktop app (Settings → Usage)")
    print(f"  Poll interval : {UPDATE_INTERVAL}s")
    print(f"  Color scale   : green (0%) → yellow (50%) → red (100%)")
    print()

    while True:
        try:
            pct = get_session_pct()
            color = pct_to_color(pct)
            status = update_orb(color)
            ts = datetime.now().strftime("%H:%M:%S")
            bar = "█" * int(pct * 20) + "░" * (20 - int(pct * 20))
            print(f"[{ts}]  {pct*100:5.1f}%  [{bar}]  {color}  (orb HTTP {status})")
        except Exception as exc:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}]  {exc}")

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
