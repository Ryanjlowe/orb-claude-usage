#!/usr/bin/env python3
"""
Claude Usage Orb Monitor

Polls Anthropic's Cost API every minute and updates an Electric Imp orb:
  Green (#00FF00) = 0% of monthly budget used
  Yellow (#FFFF00) = 50% of monthly budget used
  Red (#FF0000) = 100% of monthly budget used

Requirements:
  pip install requests

Environment variables:
  ANTHROPIC_ADMIN_API_KEY  — Admin key (sk-ant-admin...) from console.anthropic.com/settings/admin-keys
                             NOTE: requires an organization account, not an individual account
  MONTHLY_BUDGET_USD       — Your monthly spending cap in dollars (default: 50.0)
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone

ORB_URL = "https://agent.electricimp.com/WSsuAkQ6L4g5"
COST_API_URL = "https://api.anthropic.com/v1/organizations/cost_report"
UPDATE_INTERVAL = 60  # seconds


def get_config():
    key = os.environ.get("ANTHROPIC_ADMIN_API_KEY")
    if not key:
        sys.exit(
            "Error: ANTHROPIC_ADMIN_API_KEY is not set.\n\n"
            "This script requires an Admin API key (starts with sk-ant-admin...).\n"
            "Create one at: https://console.anthropic.com/settings/admin-keys\n\n"
            "Note: Admin API keys require an organization account.\n"
            "If you're on an individual account, set up an org at:\n"
            "  Console → Settings → Organization"
        )
    budget = float(os.environ.get("MONTHLY_BUDGET_USD", "50.0"))
    return key, budget


def get_month_cost_usd(api_key: str) -> float:
    """Return month-to-date spend in USD by summing the cost report."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    headers = {
        "anthropic-version": "2023-06-01",
        "x-api-key": api_key,
    }
    params = {
        "starting_at": month_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ending_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bucket_width": "1d",
    }

    total_cents = 0.0
    page = None

    while True:
        if page:
            params["page"] = page

        resp = requests.get(COST_API_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()

        for bucket in body.get("data", []):
            # API returns costs in cents as decimal strings
            for entry in bucket.get("results", []):
                total_cents += float(entry.get("cost", 0) or 0)

        if not body.get("has_more"):
            break
        page = body.get("next_page")

    return total_cents / 100.0  # cents → USD


def pct_to_color(pct: float) -> str:
    """
    Map 0.0–1.0 to a hex color:
      0.0 → green  #00FF00
      0.5 → yellow #FFFF00
      1.0 → red    #FF0000
    """
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
    api_key, budget = get_config()
    print(f"Orb monitor started")
    print(f"  Monthly budget : ${budget:.2f}")
    print(f"  Poll interval  : {UPDATE_INTERVAL}s")
    print(f"  Color scale    : green (0%) → yellow (50%) → red (100%)")
    print()

    while True:
        try:
            cost = get_month_cost_usd(api_key)
            pct = cost / budget
            color = pct_to_color(pct)
            status = update_orb(color)
            ts = datetime.now().strftime("%H:%M:%S")
            bar = "█" * int(pct * 20) + "░" * (20 - int(pct * 20))
            print(f"[{ts}]  ${cost:7.4f} / ${budget:.2f}  [{bar}] {pct*100:5.1f}%  {color}  (HTTP {status})")
        except requests.HTTPError as exc:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}]  API error: {exc.response.status_code} {exc.response.text[:120]}")
        except Exception as exc:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}]  Error: {exc}")

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
