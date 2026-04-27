#!/usr/bin/env python3
"""
Claude Desktop Usage Orb Monitor

Reads the "Current session" usage % from the Claude desktop app via
ScreenCaptureKit + Vision OCR and updates an Electric Imp orb every minute:
  Green (#00FF00) = 0%   Red (#FF0000) = 100%

Requirements:
  - Claude desktop app running with Settings → Usage page visible
  - macOS 13+ (uses ScreenCaptureKit + Swift/Vision)
  - pip3 install requests
  - swiftc get_usage.swift -o get_usage   (one-time compile)

On first run, macOS will prompt for Screen Recording permission for get_usage.
Grant it in System Settings → Privacy & Security → Screen Recording.
"""

import os
import sys
import time
import subprocess
import requests
from datetime import datetime

ORB_URL = "https://agent.electricimp.com/WSsuAkQ6L4g5"
UPDATE_INTERVAL = 60  # seconds
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GET_USAGE = os.path.join(SCRIPT_DIR, "get_usage")


def ensure_binary():
    if os.path.exists(GET_USAGE):
        return
    src = os.path.join(SCRIPT_DIR, "get_usage.swift")
    if not os.path.exists(src):
        sys.exit(f"Missing {src} — clone the full repo.")
    print("Compiling get_usage binary (one-time)...", flush=True)
    result = subprocess.run(["swiftc", src, "-o", GET_USAGE], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Compile failed:\n{result.stderr}")
    print("Done.\n", flush=True)


def get_session_pct() -> float:
    result = subprocess.run([GET_USAGE], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "get_usage failed")
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
    ensure_binary()

    print("Orb monitor started", flush=True)
    print(f"  Source        : Claude desktop (Settings → Usage)", flush=True)
    print(f"  Poll interval : {UPDATE_INTERVAL}s", flush=True)
    print(f"  Color scale   : green (0%) → yellow (50%) → red (100%)", flush=True)
    print(flush=True)

    while True:
        try:
            pct = get_session_pct()
            color = pct_to_color(pct)
            status = update_orb(color)
            ts = datetime.now().strftime("%H:%M:%S")
            bar = "█" * int(pct * 20) + "░" * (20 - int(pct * 20))
            print(f"[{ts}]  {pct*100:5.1f}%  [{bar}]  {color}  (orb HTTP {status})", flush=True)
        except Exception as exc:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}]  {exc}", flush=True)

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
