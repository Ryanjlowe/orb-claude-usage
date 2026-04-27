# orb-claude-usage

Turns an [Electric Imp](https://www.electricimp.com/) orb into a live ambient indicator of your Anthropic API spend. The orb glows green when you're at 0% of your monthly budget and fades through yellow to red as you approach 100%.

## Prerequisites

- Python 3.7+
- An Anthropic **organization** account (not an individual account)
- An Anthropic **Admin API key** (`sk-ant-admin...`) — create one at [console.anthropic.com/settings/admin-keys](https://console.anthropic.com/settings/admin-keys)

> **Note:** If you're on an individual account, you'll need to set up an organization first: Console → Settings → Organization.

## Installation

```bash
git clone https://github.com/Ryanjlowe/orb-claude-usage.git
cd orb-claude-usage
pip install requests
```

## Configuration

Set two environment variables:

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_ADMIN_API_KEY` | Your Admin API key (`sk-ant-admin...`) | *(required)* |
| `MONTHLY_BUDGET_USD` | Your monthly spend cap in dollars | `50.0` |

```bash
export ANTHROPIC_ADMIN_API_KEY="sk-ant-admin..."
export MONTHLY_BUDGET_USD="50.0"
```

## Running manually

```bash
python3 orb_monitor.py
```

Sample output:

```
Orb monitor started
  Monthly budget : $50.00
  Poll interval  : 60s
  Color scale    : green (0%) → yellow (50%) → red (100%)

[14:32:01]  $12.3400 / $50.00  [████████░░░░░░░░░░░░]  24.7%  #7EFF00  (HTTP 200)
[14:33:01]  $12.3401 / $50.00  [████████░░░░░░░░░░░░]  24.7%  #7EFF00  (HTTP 200)
```

## Running automatically every minute

### macOS — launchd (recommended)

1. Create the plist file at `~/Library/LaunchAgents/com.orb-claude-usage.plist`:

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
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_ADMIN_API_KEY</key>
        <string>sk-ant-admin...</string>
        <key>MONTHLY_BUDGET_USD</key>
        <string>50.0</string>
    </dict>
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

Replace `/path/to/orb-claude-usage/orb_monitor.py` and the API key with your actual values.

2. Load and start the agent:

```bash
launchctl load ~/Library/LaunchAgents/com.orb-claude-usage.plist
launchctl start com.orb-claude-usage
```

3. Check logs:

```bash
tail -f /tmp/orb-claude-usage.log
```

4. To stop it:

```bash
launchctl stop com.orb-claude-usage
launchctl unload ~/Library/LaunchAgents/com.orb-claude-usage.plist
```

### Linux — systemd

1. Create `/etc/systemd/system/orb-claude-usage.service`:

```ini
[Unit]
Description=Claude Usage Orb Monitor

[Service]
ExecStart=/usr/bin/python3 /path/to/orb-claude-usage/orb_monitor.py
Restart=always
Environment=ANTHROPIC_ADMIN_API_KEY=sk-ant-admin...
Environment=MONTHLY_BUDGET_USD=50.0

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

### Any OS — cron

> Note: cron restarts the script every minute rather than keeping it running. This works but adds a small startup delay each cycle.

```bash
crontab -e
```

Add this line (update paths accordingly):

```
* * * * * ANTHROPIC_ADMIN_API_KEY=sk-ant-admin... MONTHLY_BUDGET_USD=50.0 /usr/bin/python3 /path/to/orb-claude-usage/orb_monitor.py --once
```

Then add `--once` mode support to the script by replacing the `while True` loop in `main()` with a single iteration when `--once` is passed. Or just let the script run continuously under launchd/systemd instead.

## Color scale

| Usage | Color |
|---|---|
| 0% | `#00FF00` green |
| 25% | `#7FFF00` yellow-green |
| 50% | `#FFFF00` yellow |
| 75% | `#FF7F00` orange |
| 100% | `#FF0000` red |
