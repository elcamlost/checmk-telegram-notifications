import socket
import cmk.gui.config as config

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (Integer, Password, Dictionary, TextAscii,
                               Transform, Checkbox, CascadingDropdown, ListOf,
                               MonitoringState)
from cmk.gui.plugins.wato import (
    notification_parameter_registry,
    NotificationParameter,
)
from cmk.gui.plugins.wato.notifications import (
    transform_back_html_mail_url_prefix, transform_forth_html_mail_url_prefix)


@notification_parameter_registry.register
class NotificationParameterTelegram(NotificationParameter):
    @property
    def ident(self):
        return "telegram.py"

    @property
    def spec(self):
        return Dictionary(
            title=_("Call with the following parameters"),
            optional_keys=["url_prefix", "graphs"],
            elements=[
                ("telegram_bot_token",
                 Password(
                     title=_("Telegram bot token"),
                     help=
                     _("The API token for the telegram bot used to send notifications. It follows the format <tt><int>:<str></tt>."
                       ),
                     size=60)),
                ("telegram_chat_id",
                 Integer(title=_("Telegram chat ID"),
                         help=_("""
                    To get you Telegram chat ID, follow the instructions on https://docs.influxdata.com/kapacitor/v1.5/event_handlers/telegram/#get-your-telegram-chat-id
                    When the chat ID is not set here, the custom attribute <tt>TELEGRAM_CHAT_ID</tt> will be checked instead.
                    """),
                         size=15)),
                ("url_prefix",
                 TextAscii(
                     title=_("URL prefix for status links"),
                     help=
                     _("Set the prefix to use for links to the status detail pages."
                       ),
                     regex="^(http|https)://.*/check_mk/$",
                     regex_error=_(
                         "The URL must begin with <tt>http</tt> or "
                         "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
                     size=64,
                     default_value="",
                 )),
                (
                    "graphs",
                    # Dictionary(
                    #     title=_("Configure when to show graphs"),
                    #     help=_("This setting allows to configure when to send or not to send graphs to a notification. "
                    #     "Default is to always send graphs."),
                    #     elements=[
                    #         (0, Checkbox(title=_("OK"), default_value=True)),
                    #         (1, Checkbox(title=_("WARN"), default_value=True)),
                    #         (2, Checkbox(title=_("CRIT"), default_value=True)),
                    #         (3, Checkbox(title=_("UNKNOWN"), default_value=True)),
                    #     ],
                    #     optional_keys=[]
                    # )
                    ListOf(
                        MonitoringState(),
                        title=_("Configure when to show graphs"),
                        help=_(
                            "This setting allows to configure when to send or not to send graphs to a notification. "
                            "Default is to always send graphs."),
                        default_value=[0, 1, 2, 3]
                        # TODO: disable reordering
                    ))
            ])
