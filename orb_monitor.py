#!/usr/bin/env python3
"""
Claude.ai Session Usage Orb Monitor

Scrapes the "Current session" usage % from claude.ai/settings and
updates an Electric Imp orb from green (0%) to red (100%) every minute.

Requirements:
  pip install playwright requests
  playwright install chromium

First run opens a visible browser so you can log in to claude.ai.
The session is saved and reused — subsequent runs are headless.
"""

import os
import re
import sys
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

ORB_URL = "https://agent.electricimp.com/WSsuAkQ6L4g5"
CLAUDE_SETTINGS_URL = "https://claude.ai/settings"
UPDATE_INTERVAL = 60  # seconds
SESSION_DIR = os.path.expanduser("~/.orb-claude-usage-session")


def pct_to_color(pct: float) -> str:
    """Green (0%) → Yellow (50%) → Red (100%)"""
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


def get_session_pct(page) -> float:
    """Navigate to claude.ai/settings and extract Current session usage %."""
    page.goto(CLAUDE_SETTINGS_URL, wait_until="networkidle", timeout=30_000)

    body_text = page.inner_text("body")
    lines = body_text.splitlines()

    for i, line in enumerate(lines):
        if "Current session" in line:
            # The percentage appears within a few lines of the label
            nearby = "\n".join(lines[max(0, i - 2) : i + 6])
            match = re.search(r"(\d+)%\s*used", nearby)
            if match:
                return int(match.group(1)) / 100.0

    raise ValueError(
        "Could not find 'Current session' percentage on claude.ai/settings.\n"
        "Make sure you are logged in and the Usage section is visible."
    )


def is_logged_in(page) -> bool:
    page.goto("https://claude.ai", wait_until="networkidle", timeout=30_000)
    return "login" not in page.url


def main():
    os.makedirs(SESSION_DIR, exist_ok=True)

    # Detect first-time setup (no saved session yet)
    first_run = not os.path.exists(os.path.join(SESSION_DIR, "Default", "Cookies"))

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False if first_run else True,
            viewport={"width": 1280, "height": 800},
            args=["--no-sandbox"],
        )
        page = context.new_page()

        if first_run or not is_logged_in(page):
            print("Opening browser — please log in to claude.ai, then press Enter here.")
            page.goto("https://claude.ai/login", wait_until="domcontentloaded")
            input("Press Enter once you are logged in: ")
            # Reopen headless for the monitoring loop
            context.close()
            context = p.chromium.launch_persistent_context(
                SESSION_DIR,
                headless=True,
                args=["--no-sandbox"],
            )
            page = context.new_page()

        print("Orb monitor started")
        print(f"  Source         : claude.ai Current session usage")
        print(f"  Poll interval  : {UPDATE_INTERVAL}s")
        print(f"  Color scale    : green (0%) → yellow (50%) → red (100%)")
        print()

        while True:
            try:
                pct = get_session_pct(page)
                color = pct_to_color(pct)
                status = update_orb(color)
                ts = datetime.now().strftime("%H:%M:%S")
                bar = "█" * int(pct * 20) + "░" * (20 - int(pct * 20))
                print(f"[{ts}]  {pct*100:5.1f}%  [{bar}]  {color}  (orb HTTP {status})")
            except Exception as exc:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}]  Error: {exc}")

            time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
