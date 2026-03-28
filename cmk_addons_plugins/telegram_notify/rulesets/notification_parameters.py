#!/usr/bin/env python3
# Telegram notification parameters for Checkmk
# Uses the cmk.rulesets.v1 API (Checkmk 2.4+)

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    Integer,
    MultilineText,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange
from cmk.rulesets.v1.rule_specs import NotificationParameters, Topic

_default_host_template = (
    "<b>$NOTIFICATIONTYPE$: $LINKEDHOSTNAME$ $EVENT_TXT$</b>\n"
    "<code>\n"
    "Host:     $HOSTNAME$\n"
    "Alias:    $HOSTALIAS$\n"
    "Address:  $HOSTADDRESS$\n"
    "Event:    $EVENT_TXT$\n"
    "Output:   $HOSTOUTPUT$\n"
    "\n"
    "Detail:\n"
    "$LONGHOSTOUTPUT$\n"
    "</code>"
)

_default_service_template = (
    "<b>$NOTIFICATIONTYPE$: $LINKEDSERVICEDESC$ $EVENT_TXT$</b>\n"
    "<code>\n"
    "Host:     $HOSTNAME$\n"
    "Alias:    $HOSTALIAS$\n"
    "Address:  $HOSTADDRESS$\n"
    "Service:  $SERVICEDESC$\n"
    "Event:    $EVENT_TXT$\n"
    "Output:   $SERVICEOUTPUT$\n"
    "\n"
    "Detail:\n"
    "$LONGSERVICEOUTPUT$\n"
    "</code>"
)

_template_help = Help(
    "Use Telegram-compatible HTML and Checkmk macros. "
    "If your template contains unescaped invalid HTML characters, sending notifications will fail with HTTP 400.<br>"
    "Plugin-specific macros:<br>"
    "- <tt>$EVENT_TXT$</tt>: State transition, e.g. 'OK -&gt; CRIT'<br>"
    "- <tt>$LINKEDHOSTNAME$</tt>: Hostname linked to the host status page<br>"
    "- <tt>$LINKEDSERVICEDESC$</tt>: Service description linked to the service status page"
)


def _form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Telegram"),
        elements={
            "telegram_bot_token": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Telegram bot token"),
                    help_text=Help(
                        "The API token for the Telegram bot used to send notifications. "
                        "Format: <tt>&lt;int&gt;:&lt;str&gt;</tt>."
                    ),
                    custom_validate=[
                        LengthInRange(
                            min_value=1,
                            error_msg=Message("Please enter the bot token"),
                        )
                    ],
                ),
            ),
            "telegram_chat_id": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Telegram chat ID"),
                    help_text=Help(
                        "The ID of the Telegram chat to send notifications to. "
                        "When not set here, the custom attribute <tt>TELEGRAM_CHAT_ID</tt> will be used instead."
                    ),
                ),
            ),
            "url_prefix": DictElement(
                parameter_form=String(
                    title=Title("URL prefix for status links"),
                    help_text=Help(
                        "Set the prefix to use for links to the status detail pages. "
                        "Must begin with <tt>http://</tt> or <tt>https://</tt> and end with <tt>/check_mk/</tt>."
                    ),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "telegram_host_template": DictElement(
                parameter_form=MultilineText(
                    title=Title("Host notification template"),
                    help_text=_template_help,
                    prefill=DefaultValue(_default_host_template),
                    monospaced=True,
                ),
            ),
            "telegram_service_template": DictElement(
                parameter_form=MultilineText(
                    title=Title("Service notification template"),
                    help_text=_template_help,
                    prefill=DefaultValue(_default_service_template),
                    monospaced=True,
                ),
            ),
            "telegram_graph_config": DictElement(
                parameter_form=Dictionary(
                    title=Title("Send performance graphs"),
                    help_text=Help("Configure for which host/service states graphs should be included."),
                    elements={
                        "ok": DictElement(
                            parameter_form=BooleanChoice(
                                title=Title("OK"),
                                prefill=DefaultValue(True),
                            ),
                        ),
                        "warn": DictElement(
                            parameter_form=BooleanChoice(
                                title=Title("WARN"),
                                prefill=DefaultValue(True),
                            ),
                        ),
                        "crit": DictElement(
                            parameter_form=BooleanChoice(
                                title=Title("CRIT"),
                                prefill=DefaultValue(True),
                            ),
                        ),
                        "unknown": DictElement(
                            parameter_form=BooleanChoice(
                                title=Title("UNKNOWN"),
                                prefill=DefaultValue(True),
                            ),
                        ),
                    },
                ),
            ),
            "telegram_socks5_proxy": DictElement(
                parameter_form=Dictionary(
                    title=Title("SOCKS5 proxy"),
                    help_text=Help(
                        "Configure an optional SOCKS5 proxy for Telegram API requests. "
                        "Username and password must both be set or both left empty."
                    ),
                    elements={
                        "server": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Server"),
                                help_text=Help("Hostname or IP address of the SOCKS5 proxy server."),
                                custom_validate=[
                                    LengthInRange(
                                        min_value=1,
                                        error_msg=Message("Please enter the proxy server address"),
                                    )
                                ],
                            ),
                        ),
                        "port": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Port"),
                                prefill=DefaultValue(80),
                                custom_validate=[
                                    NumberInRange(
                                        min_value=1,
                                        max_value=65535,
                                        error_msg=Message("Port must be between 1 and 65535"),
                                    )
                                ],
                            ),
                        ),
                        "user": DictElement(
                            parameter_form=String(
                                title=Title("Username"),
                                help_text=Help("Username for proxy authentication."),
                            ),
                        ),
                        "password": DictElement(
                            parameter_form=Password(
                                title=Title("Password"),
                                help_text=Help("Password for proxy authentication."),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_telegram_notify = NotificationParameters(
    name="telegram",
    title=Title("Telegram"),
    topic=Topic.NOTIFICATIONS,
    parameter_form=_form_spec,
)
