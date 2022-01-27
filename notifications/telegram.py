#!/usr/bin/env python3
# Telegram
"Send Checkmk notifications to Telegram groups by using a bot"

import base64
from ctypes import Union
import os
import json
from sys import stderr, exit as s_exit
from typing import Callable, Dict, List, Optional, Tuple, Any
import requests
from cmk.notification_plugins import utils
from cmk.notification_plugins.mail import event_templates
from cmk.utils import site

# TODO: Add logging to allow better troubleshooting of issues?
# TODO: Add bulk


def is_service_notification(context: dict) -> bool:
    "Decide whether a notification context is a service notification"
    return context["WHAT"] == "SERVICE"


class GraphFetcher():
    "Render graphs from Checkmk"

    def __init__(self, context: dict) -> None:
        self.hostname = context["HOSTNAME"]

        if is_service_notification(context):
            self.svc_desc = context["SERVICEDESC"]
        else:
            self.svc_desc = "_HOST_"

    def render_performance_graphs(self) -> List[Tuple[str, str]]:
        "Get performance graphs from Checkmk and return a list of (filename, b64 data)"
        url = "http://localhost:%d/%s/check_mk/ajax_graph_images.py" % (
            site.get_apache_port(),
            os.environ["OMD_SITE"],
        )

        try:
            json_data = requests.get(
                url,
                {
                    "host": self.hostname,
                    "service": self.svc_desc,
                    "num_graphs": 10  # this is the maximum allowed by Telegram
                }).json()
        except (requests.RequestException, json.JSONDecodeError) as ex:
            stderr.write("ERROR: Failed to fetch graphs: %s\nURL: %s\n" %
                         (ex, url))
            return []

        attachments = []
        for i, base64_source in enumerate(json_data):
            filename = '%s-%s-%d.png' % (self.hostname, self.svc_desc, i)
            attachments.append((filename, base64.b64decode(base64_source)))

        return attachments


class TelegramConfig():
    "Configuration container for the Telegram notifier"
    graph_config_field_name = "PARAMETER_TELEGRAM_GRAPH_CONFIG"
    bot_token_field_name = "PARAMETER_TELEGRAM_BOT_TOKEN"
    chat_id_field_names = [
        "PARAMETER_TELEGRAM_CHAT_ID",  # for notification parameters
        "CONTACT_TELEGRAM_CHAT_ID"  # for custom attributes
    ]

    host_template_field_name = "PARAMETER_TELEGRAM_HOST_TEMPLATE"
    default_host_template = "<b>$NOTIFICATIONTYPE$: $LINKEDHOSTNAME$ $EVENT_TXT$</b>\n" + \
                      "<code>\n" + \
                      "Host:     $HOSTNAME$\n"+ \
                      "Alias:    $HOSTALIAS$\n" + \
                      "Address:  $HOSTADDRESS$\n" + \
                      "Event:    $EVENT_TXT$\n" + \
                      "Output:   $HOSTOUTPUT$\n" + \
                      "\n" + \
                      "Detail:\n" + \
                      "$LONGHOSTOUTPUT$\n" + \
                      "</code>"

    service_template_field_name = "PARAMETER_TELEGRAM_SERVICE_TEMPLATE"
    default_service_template = "<b>$NOTIFICATIONTYPE$: $LINKEDSERVICEDESC$ $EVENT_TXT$</b>\n" + \
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

    def __init__(self):
        self.__context = utils.collect_context()
        self._extend_context()
        self._escape_html_output()
        self.__bot_token = None
        self.__chat_id = None

    # Protected helpers
    def _extend_context(self):
        "Enrich context by some custom fields"
        event_txt, _ = event_templates(self.__context["NOTIFICATIONTYPE"])
        self.__context["EVENT_TXT"] = utils.substitute_context(
            event_txt.replace("@", self.__context["WHAT"]), self.__context)

        self.__context["LINKEDHOSTNAME"] = utils.format_link(
            '<a href="%s">%s</a>', utils.host_url_from_context(self.__context),
            self.__context["HOSTNAME"])

        self.__context["LINKEDSERVICEDESC"] = utils.format_link(
            '<a href="%s">%s</a>',
            utils.service_url_from_context(self.__context),
            self.__context.get("SERVICEDESC", ''))

    def _escape_html_output(self):
        "Escape any HTML characters in output and long output"

        # NOTE: There is utils.html_escape_context. Since we need HTML tags
        # in the templates, we may not use it, though.
        output = "%sOUTPUT" % self.__context["WHAT"]
        long_output = "LONG%sOUTPUT" % self.__context["WHAT"]
        for search, replace in [("<", "&lt;"), (">", "&gt;")]:
            self.__context[output] = self.__context[output].replace(
                search, replace)
            self.__context[long_output] = self.__context[long_output].replace(
                search, replace)

    @property
    def _notification_status(self):
        return int(self.__context["%sSTATEID" % self.__context["WHAT"]])

    @property
    def _should_send_graphs(self):
        send_list = []

        for setting in filter(
                lambda e: e.startswith(self.graph_config_field_name),
                self.__context):
            if self.__context[setting] == "True":
                # variables are named <GRAPH_CONFIG_FIELD>_X where X is the checkmk status ID
                send_list.append(int(setting[-1]))

        return self._notification_status in send_list

    # Publics
    @property
    def performance_graphs(self) -> Union[List, List[Tuple[str, str]]]:
        "Return performance graphs if enabled, otherwise empty list"
        if self._should_send_graphs:
            return GraphFetcher(self.__context).render_performance_graphs()
        return []

    @property
    def bot_token(self) -> str:
        "Fetch the bot token from notification context"
        if not self.__bot_token:
            if self.bot_token_field_name in self.__context:
                self.__bot_token = self.__context[self.bot_token_field_name]
                self.__bot_token = utils.retrieve_from_passwordstore(
                    self.__bot_token)
            else:
                raise AttributeError("Unable to find context variable '%s'" %
                                     self.bot_token_field_name)
        return self.__bot_token

    @property
    def chat_id(self) -> str:
        "Fetch the chat ID from notification context"
        if not self.__chat_id:
            for fieldname in self.chat_id_field_names:
                if fieldname in self.__context and self.__context[
                        fieldname] != 0:
                    self.__chat_id = self.__context[fieldname]
                    break
            else:
                raise AttributeError(
                    "Unable to find chat ID in any field: %s" %
                    ",".join(self.chat_id_field_names))
        return self.__chat_id

    @property
    def notification_content(self) -> str:
        "Format the text of the notification based on the context"
        if is_service_notification(self.__context):
            template = self.__context.setdefault(
                self.service_template_field_name,
                self.default_service_template)
        else:
            template = self.__context.setdefault(self.host_template_field_name,
                                                 self.default_host_template)

        text = utils.substitute_context(template, self.__context)

        return text.replace("\\n", "\n")


def exit_on_nonzero_only(func: Callable[[Any], None]) -> Callable[[Any], None]:
    "Keep the program running if exit code is 0, otherwise exit"

    def wrap(*args):
        exit_code = 0
        try:
            func(*args)
        except SystemExit as ex:
            exit_code = ex.code
        finally:
            if exit_code != 0:
                s_exit(exit_code)

    return wrap


class TelegramNotifier():
    "Send checkmk notifications to Telegram"

    def __init__(self, config: TelegramConfig) -> None:
        self.__config = config

    def _base_url(self,
                  endpoint: str,
                  hide_token: Optional[bool] = False) -> str:
        return "https://api.telegram.org/bot%s/%s" % (
            self.__config.bot_token if not hide_token else "****", endpoint)

    def _api_command(self,
                     endpoint: str,
                     files: Optional[Union[Dict[str, Tuple[str, str]],
                                           List[Tuple[str, str]]]] = None,
                     **kwargs) -> None:
        # NOTE: There is utils.post_request. However, this function assumes
        # that context is not modified before submission. Thus, we may not use it.
        json_data = dict({"chat_id": self.__config.chat_id}, **kwargs)

        if not files:
            response = requests.post(url=self._base_url(endpoint),
                                     json=json_data,
                                     files=files)
        else:  # when sending files we need to also send parameters using multipart/form-data
            response = requests.post(url=self._base_url(endpoint),
                                     data=json_data,
                                     files=files)

        utils.process_by_status_code(response)

    def _send_message(self, text: str) -> None:
        self._api_command(
            "sendMessage", **{
                "text": text,
                "disable_web_page_preview": True,
                "parse_mode": "html"
            })

    @exit_on_nonzero_only
    def _send_photo(self, photo_data: Tuple[str, str]) -> None:
        # We could use the 'caption' property here to send an image description.
        # However, the caption is limited to 1000 characters. Sending just the
        # image and a separate text message is easier.
        self._api_command("sendPhoto",
                          files={"photo": photo_data},
                          **{
                              "parse_mode": "html",
                              "disable_notification": True,
                          })

    @exit_on_nonzero_only
    def _send_mediagroup(self, photo_data: List[Tuple[str, str]],
                         media_description: List[Dict[str, str]]) -> None:
        """
        Send multiple media to telegram as one album.
        photo_data => a key-value mapping in the format 'filename': 'image data'
        media_description => a list of dicts telling telegram, what images are in photo_data

        https://core.telegram.org/bots/api#sendmediagroup
        https://core.telegram.org/bots/api#inputmediaphoto
        https://github.com/php-telegram-bot/core/issues/811
        """

        # We could use the 'caption' property here to send an image description
        # for the last media element. However, the caption is limited to 1000
        # characters. Sending just the images and a separate text message is easier.

        self._api_command("sendMediaGroup",
                          files=photo_data,
                          **{
                              "disable_notification": True,
                              "media": json.dumps(media_description)
                          })

    def notify(self) -> None:
        "Start the notification process"
        text = self.__config.notification_content

        try:
            attachments = self.__config.performance_graphs

            if len(attachments
                   ) == 1:  # exactly one picture, send as photo with caption
                _, att_data = attachments[0]
                self._send_photo(att_data)

            elif len(attachments) > 1:  # more than one picture, send as album
                telegram_media = []  # media description list for telegram API
                media_data = {}  # the actual image data
                for att_name, att_data in attachments:
                    telegram_media.append({
                        "type": "photo",
                        "media": "attach://%s" % att_name
                    })

                    media_data[att_name] = att_data

                self._send_mediagroup(media_data, telegram_media)

            # always send the notification text in a separate message to avoid length limitations
            self._send_message(text)

        except AttributeError as atterr:
            stderr.write(repr(atterr))
            s_exit(2)


if __name__ == "__main__":
    TelegramNotifier(TelegramConfig()).notify()
