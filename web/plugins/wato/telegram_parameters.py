from cmk.gui.i18n import _
from cmk.gui.valuespec import Integer, Password, Dictionary
from cmk.gui.plugins.wato import (
    notification_parameter_registry,
    NotificationParameter,
)


@notification_parameter_registry.register
class NotificationParameterTelegram(NotificationParameter):
    @property
    def ident(self):
        return "telegram.py"

    @property
    def spec(self):
        return Dictionary(elements=[
            (
                "telegram_bot_token",
                Password(
                    title=_("Telegram bot token"),
                    help=_("The API token for the telegram bot used to send notifications. It follows the format <tt><int>:<str></tt>."),
                    allow_empty=False,
                    size=60
                )
            ),
            (
                "telegram_chat_id",
                Integer(
                    title=_("Telegram chat ID"),
                    help=
                    _("""
                    To get you Telegram chat ID, follow the instructions on https://docs.influxdata.com/kapacitor/v1.5/event_handlers/telegram/#get-your-telegram-chat-id
                    When the chat ID is not set here, the custom attribute <tt>TELEGRAM_CHAT_ID</tt> will be checked instead.
                    """),
                    allow_empty=False,
                    size=15
                )            
            ),
            ])
