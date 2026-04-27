# orb-claude-usage

Turns an [Electric Imp](https://www.electricimp.com/) orb into a live ambient indicator of your Claude.ai session usage. The orb glows green when you're at 0% of your current session limit and fades through yellow to red as you approach 100%.

The "Current session" percentage comes from **claude.ai → Settings → Usage**, which shows your rolling 5-hour rate limit usage (the same number you see in the Claude desktop/web app).

## Prerequisites

- Python 3.8+
- A Claude.ai account (any plan)

## Installation

```bash
git clone https://github.com/Ryanjlowe/orb-claude-usage.git
cd orb-claude-usage
pip install playwright requests
playwright install chromium
```

## First run — log in

The first time you run the script, it opens a visible Chromium browser so you can log in to claude.ai. Your session is saved locally and reused for all future runs (headless).

```bash
python3 orb_monitor.py
```

You'll see:

```
Opening browser — please log in to claude.ai, then press Enter here.
Press Enter once you are logged in:
```

Log in to claude.ai in the browser window, then come back to the terminal and press Enter. The browser closes and headless polling begins.

## Normal operation

After the first login, just run:

```bash
python3 orb_monitor.py
```

Sample output:

```
Orb monitor started
  Source         : claude.ai Current session usage
  Poll interval  : 60s
  Color scale    : green (0%) → yellow (50%) → red (100%)

[14:32:01]   45.0%  [█████████░░░░░░░░░░░]  #FFBE00  (orb HTTP 200)
[14:33:01]   45.0%  [█████████░░░░░░░░░░░]  #FFBE00  (orb HTTP 200)
```

Your session cookie is stored at `~/.orb-claude-usage-session/`. Delete that folder to force a fresh login.

## Running automatically every minute

The script runs its own polling loop — just keep it running in the background.

### macOS — launchd (recommended)

1. Create the plist at `~/Library/LaunchAgents/com.orb-claude-usage.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.orb-claude-usage</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/orb-claude-usage/orb_monitor.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/orb-claude-usage.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/orb-claude-usage.log</string>
</dict>
</plist>
```

Replace `/path/to/orb-claude-usage/orb_monitor.py` with the actual path.

2. Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.orb-claude-usage.plist
launchctl start com.orb-claude-usage
```

3. Check logs:

```bash
tail -f /tmp/orb-claude-usage.log
```

4. To stop:

```bash
launchctl stop com.orb-claude-usage
launchctl unload ~/Library/LaunchAgents/com.orb-claude-usage.plist
```

> **Note:** Run the script manually once first (`python3 orb_monitor.py`) to complete the login flow before loading it as a launchd service.

### Linux — systemd

1. Create `/etc/systemd/system/orb-claude-usage.service`:

```ini
[Unit]
Description=Claude Usage Orb Monitor

[Service]
ExecStart=/usr/bin/python3 /path/to/orb-claude-usage/orb_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now orb-claude-usage
```

3. Check logs:

```bash
journalctl -u orb-claude-usage -f
```

> **Note:** Run manually first to complete the login flow before enabling the service.

## Color scale

| Usage | Color |
|---|---|
| 0% | `#00FF00` green |
| 25% | `#7FFF00` yellow-green |
| 50% | `#FFFF00` yellow |
| 75% | `#FF7F00` orange |
| 100% | `#FF0000` red |

## How it works

Every 60 seconds, a headless Chromium browser navigates to `claude.ai/settings`, reads the "Current session X% used" value from the page, maps it to a color on the green→red gradient, and POSTs that color to the Electric Imp orb endpoint.
