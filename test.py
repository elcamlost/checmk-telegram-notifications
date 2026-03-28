#!/usr/bin/env python3

import ast
import importlib.util
import os
from importlib.machinery import SourceFileLoader
from pathlib import Path

_path = str(Path(__file__).parent / "notifications" / "telegram")
_loader = SourceFileLoader("telegram_plugin", _path)
_spec = importlib.util.spec_from_file_location("telegram_plugin", _path, loader=_loader)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
TelegramConfig = _module.TelegramConfig
TelegramNotifier = _module.TelegramNotifier

CONFIG_FILE = "test.cfg"

# try reading config file
if os.path.isfile(CONFIG_FILE):
    update_context = ast.literal_eval(open(CONFIG_FILE, encoding="utf-8").read())
else:
    config = {
        "PARAMETER_TELEGRAM_CHAT_ID": ("Telegram chat ID", int),
        "PARAMETER_TELEGRAM_BOT_TOKEN": ("Telegram bot token", lambda v: f"password	{v.strip()}"),
        "LINKEDSERVICEDESC": ("Full site URL", lambda v: f"<a href='{v.strip()}'>Some linked service</a>"),
        "HOSTNAME": ("a hostname to send the notification for", str.strip),
    }
    update_context = {}
    for key, user_input in config.items():
        update_context[key] = user_input[1](input(f"Enter {user_input[0]}: "))

    with open(CONFIG_FILE, "w+", encoding="utf-8") as cfg:
        cfg.write(repr(update_context))


base_context = {
    "NOTIFICATIONTYPE":
    "PROBLEM",
    "SERVICESHORTSTATE":
    "CRIT",
    "WHAT":
    "SERVICE",
    "PREVIOUSSERVICEHARDSHORTSTATE":
    "OK",
    "SERVICESTATEID":
    "2",
    "HOSTALIAS":
    "notification-test",
    "HOSTADDRESS":
    "192.168.1.1",
    "SERVICEDESC":
    "some service",
    "SERVICEOUTPUT":
    "Some very long output with LT: <3",
    "LONGSERVICEOUTPUT":
    "Some very very\\nvery very very very very very\\nvery very very very very very very\\nvery very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very long output"
}

base_context.update(update_context)

for k, v in base_context.items():
    os.environ["NOTIFY_%s" % k] = str(v)

TelegramNotifier(TelegramConfig()).notify()
