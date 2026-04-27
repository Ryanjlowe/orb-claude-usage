# orb-claude-usage

Turns an [Electric Imp](https://www.electricimp.com/) orb into a live ambient indicator of your Claude.ai session usage. The orb glows green when you're at 0% of your current session limit and fades through yellow to red as you approach 100%.

Reads the "Current session" percentage directly from the **Claude desktop app** using macOS screencapture + Vision OCR — no API keys, no browser scraping, no bot detection.

## How it works

Every 60 seconds:
1. Finds the Claude desktop app window
2. Takes a screenshot (`screencapture`)
3. Runs Apple Vision OCR to read the "Current session X% used" value
4. Maps the percentage to a color on the green → red gradient
5. POSTs that color to the Electric Imp orb

## Prerequisites

- macOS (uses `screencapture` and the built-in Vision framework)
- Claude desktop app running with **Settings → Usage** page visible
- Python 3.8+ with `requests`
- Xcode Command Line Tools (for `swiftc`)

## Installation

```bash
git clone https://github.com/Ryanjlowe/orb-claude-usage.git
cd orb-claude-usage

# Compile the OCR binary (one-time, takes ~10 seconds)
swiftc get_usage.swift -o get_usage

# Install Python dependency
pip3 install requests
```

## Usage

1. Open the Claude desktop app and navigate to **Settings → Usage**
   (the "Current session" bar must be visible on screen)

2. Run the monitor:

```bash
python3 orb_monitor.py
```

Sample output:

```
Orb monitor started
  Source        : Claude desktop app (Settings → Usage)
  Poll interval : 60s
  Color scale   : green (0%) → yellow (50%) → red (100%)

[14:32:01]   63.0%  [████████████░░░░░░░░]  #FFBC00  (orb HTTP 200)
[14:33:01]   63.0%  [████████████░░░░░░░░]  #FFBC00  (orb HTTP 200)
```

## Running automatically every minute

The script runs its own polling loop — just keep it running in the background.

> **Note:** Run the script manually first to confirm it's working before setting up autostart.

### macOS — launchd (recommended)

1. Create `~/Library/LaunchAgents/com.orb-claude-usage.plist`:

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

## Color scale

| Usage | Color |
|---|---|
| 0% | `#00FF00` green |
| 25% | `#7FFF00` yellow-green |
| 50% | `#FFFF00` yellow |
| 75% | `#FF7F00` orange |
| 100% | `#FF0000` red |
