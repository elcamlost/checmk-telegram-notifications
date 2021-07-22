import socket
import cmk.gui.config as config

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (Integer, Password, Dictionary, TextAscii,
                               Transform, Checkbox, CascadingDropdown, ListOf,
                               MonitoringState, TextAreaUnicode)
from cmk.gui.plugins.wato import (
    notification_parameter_registry,
    NotificationParameter,
    IndividualOrStoredPassword
)
from cmk.gui.plugins.wato.notifications import (
    transform_back_html_mail_url_prefix, transform_forth_html_mail_url_prefix)

_telegram_template_help = lambda what: _("Use telegram-compatible HTML, and checkmk macros to define the content to be shown in %s notifications. " % (what) + \
    "If your template contains unescaped, 'Telegram-invalid' HTML characters, sending notifications will fail with HTTP 400 Bad Request.<br>"
    "You may use any checkmk macro, all custom macros that are available as well as the following plugin specific macros:<br>"
    "- <tt>EVENT_TXT</tt>: Shows the state transition like 'OK -> CRIT'<br>"
    "- <tt>LINKEDHOSTNAME</tt>: Is replaced by the hostname linked to the host status page on checkmk<br>"
    "- <tt>LINKEDSERVICEDESC</tt>: Is replaced by 'hostname/service' linked to the service status page on checkmk<br>"
                                         )


@notification_parameter_registry.register
class NotificationParameterTelegram(NotificationParameter):
    @property
    def ident(self):
        return "telegram.py"

    @property
    def spec(self):
        return Dictionary(
            title=_("Call with the following parameters"),
            required_keys=["telegram_bot_token", "telegram_chat_id"],
            elements=
            [("telegram_bot_token",
              IndividualOrStoredPassword(
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
                  "telegram_host_template",
                  TextAreaUnicode(
                      title=_("Configure notification content for host notifications"),
                      help=_telegram_template_help("host"),
                      cols=100,
                      rows=15,
                      monospaced=True,
                      allow_empty=False,
                      default_value="<b>$NOTIFICATIONTYPE$: $LINKEDHOSTNAME$ $EVENT_TXT$</b>\n" + \
                      "<code>\n" +  \
                      "Host:     $HOSTNAME$\n"+ \
                      "Alias:    $HOSTALIAS$\n" + \
                      "Address:  $HOSTADDRESS$\n" + \
                      "Event:    $EVENT_TXT$\n" + \
                      "Output:   $HOSTOUTPUT$\n" + \
                      "\n" + \
                      "Detail:\n" + \
                      "$LONGHOSTOUTPUT$\n" + \
                      "</code>"
                  )
              ),
              (
                  "telegram_service_template",
                  TextAreaUnicode(
                      title=_("Configure notification content for service notifications"),
                      help=_telegram_template_help("service"),
                      cols=100,
                      rows=15,
                      monospaced=True,
                      allow_empty=False,
                      default_value="<b>$NOTIFICATIONTYPE$: $LINKEDSERVICEDESC$ $EVENT_TXT$</b>\n" + \
                      "<code>\n" + \
                      "Host:     $HOSTNAME$\n" + \
                      "Alias:    $HOSTALIAS$\n" + \
                      "Address:  $HOSTADDRESS$\n" + \
                      "Service:  $SERVICEDESC$\n" + \
                      "Event:    $EVENT_TXT$\n" + \
                      "Output:   $SERVICEOUTPUT$\n" + \
                      "\n" + \
                      "Detail:\n" + \
                      "$LONGSERVICEOUTPUT$\n" + \
                      "</code>"
                  )
              ),
              # A dictionary gets serialized like follows:
              # 'NOTIFY_PARAMETER_TELEGRAM_GRAPH_CONFIG_0': 'True',
              # 'NOTIFY_PARAMETER_TELEGRAM_GRAPH_CONFIG_1': 'True',
              # 'NOTIFY_PARAMETER_TELEGRAM_GRAPH_CONFIG_2': 'True',
              # 'NOTIFY_PARAMETER_TELEGRAM_GRAPH_CONFIG_3': 'True',
             ("telegram_graph_config",
              Dictionary(
                  title=_("Configure when to show graphs"),
                  help=_(
                      "This setting allows to configure when to send or not to send graphs to a notification. "
                      "Default is to always send graphs."),
                  elements=[
                      ("0",
                       Checkbox(title=_("OK"),
                                default_value=True,
                                label=_("when state is OK"))),
                      ("1",
                       Checkbox(title=_("WARN"),
                                default_value=True,
                                label=_("when state is WARN"))),
                      ("2",
                       Checkbox(title=_("CRIT"),
                                default_value=True,
                                label=_("when state is CRIT"))),
                      ("3",
                       Checkbox(title=_("UNKNOWN"),
                                default_value=True,
                                label=_("when state is UNKNOWN"))),
                  ],
                  optional_keys=[]))
             ])
