# Checkmk Telegram Notification Plugin

[![codecov](https://codecov.io/gh/elcamlost/checkmk_notify_telegram/branch/main/graph/badge.svg)](https://codecov.io/gh/elcamlost/checkmk_notify_telegram)

A Checkmk notification plugin that sends monitoring alerts to a Telegram chat via a bot. Supports plain text notifications and performance graphs.

Requires **Checkmk 2.3+**.

## Setup

### 1. Create a Telegram bot

- Talk to [@BotFather](https://core.telegram.org/bots#6-botfather) and create a new bot
- Copy the bot token (format: `<int>:<str>`)

### 2. Get your chat ID

Send at least one message to your bot or group, then run:

```bash
BOT_TOKEN="<YOUR BOT TOKEN>"
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" | grep '"chat"' -A 3 | grep '"id"'
```

### 3. Install the plugin

Build the MKP package:

```bash
python3 package.py
```

Install on your Checkmk site:

```bash
mkp install telegram_notify.mkp
```

### 4. Configure a notification rule

In Checkmk go to **Setup → Notifications** and create a new rule using the **Telegram** method. Set at minimum:

- **Bot token** — from BotFather (supports the Checkmk password store)
- **Chat ID** — from step 2 above (or set the custom attribute `TELEGRAM_CHAT_ID` per contact)

### Optional: SOCKS5 proxy

If your Checkmk server cannot reach `api.telegram.org` directly, configure a SOCKS5 proxy in the notification parameters. Username and password are optional and support the Checkmk password store.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install ".[dev]"
.venv/bin/pytest -v
```

For manual end-to-end testing (sends a real notification):

```bash
.venv/bin/python test.py
```
