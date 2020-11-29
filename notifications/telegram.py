#!/usr/bin/env python3
# Telegram

# TODO: Test whether the new code works
import os
import json
import requests
from sys import stderr, exit as s_exit

from cmk.notification_plugins import utils
from cmk.notification_plugins.mail import render_performance_graphs


class TelegramConfig():
    graph_config_field_name = "PARAMETER_TELEGRAM_GRAPH_CONFIG"
    bot_token_field_name = "PARAMETER_TELEGRAM_BOT_TOKEN"
    chat_id_field_names = [
        "PARAMETER_TELEGRAM_CHAT_ID",  # for notification parameters
        "CONTACT_TELEGRAM_CHAT_ID"  # for custom attributes
    ]

    notification_host_template = """<b>$NOTIFICATIONTYPE$: <a href="%s">$HOSTNAME$</a> $EVENT_TXT$</b>
<code>
Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$

Detail:
$LONGHOSTOUTPUT$
</code>"""

    notification_service_template = """<b>$NOTIFICATIONTYPE$: <a href="%s">$HOSTNAME$/$SERVICEDESC$</a> $EVENT_TXT$</b>
<code>
Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$

Detail:
$LONGSERVICEOUTPUT$
</code>"""

    def __init__(self):
        self.__context = utils.collect_context()
        self.__bot_token = None
        self.__chat_id = None

    def _replace_newlines(self, text):
        return text.replace("\\n", "\n")

    @property
    def __is_service_notification(self):
        return self.__context["WHAT"] == "SERVICE"

    @property
    def __notification_status(self):
        if not self.__notification_status:
            if self.__is_service_notification:
                return int(self.__context["SERVICESTATEID"])
            else:
                return int(self.__context["HOSTSTATEID"])

    @property
    def should_send_graph(self):
        send_list = []

        for setting in filter(lambda e: e.startswith(self.graph_config_field_name), self.__context):
            if self.__context[setting] == "True":
                # variables are named <GRAPH_CONFIG_FIELD>_X where X is the checkmk status ID
                send_list.append(int(setting[-1]))

        return self.__notification_status in send_list

    @property
    def performance_graphs(self):
        return render_performance_graphs(self.__context)

    @property
    def bot_token(self):
        if not self.__bot_token:
            if self.bot_token_field_name in self.__context:
                self.__bot_token = self.__context[self.bot_token_field_name]
            raise AttributeError("Unable to find context variable '%s'" %
                                 self.bot_token_field_name)
        return self.__bot_token

    @property
    def chat_id(self):
        if self.__chat_id:
            for fieldname in self.chat_id_field_names:
                if fieldname in self.__context and self.__context[
                        fieldname] != 0:
                    self.__chat_id = self.__context[fieldname]
            raise AttributeError("Unable to find chat ID in any field: %s" %
                                 ",".join(self.chat_id_field_names))
        return self.__chat_id

    @property
    def notification_content(self):
        if self.__is_service_notification:
            text = self.notification_service_template % utils.service_url_from_context(self.__context)
        else:
            text = self.notification_host_template % utils.host_url_from_context(self.__context)
        text = utils.substitute_context(text, self.__context)
        text = self._replace_newlines(text)

        return text
    

class TelegramNotifier():
    def __init__(self, config):
        self.__config = config

    def _base_url(self, endpoint, hide_token=False):
        return "https://api.telegram.org/bot%s/%s" % (
            self.__config.bot_token if not hide_token else "****", endpoint)

    def _api_command(self, endpoint, context, files=None, **kwargs):
        json_data = dict({"chat_id": self.__config.chat_id}, **kwargs)

        if not files:
            response = requests.post(url=self._base_url(endpoint),
                                     json=json_data,
                                     files=files)
        else:  # when sending files we need to also send parameters using multipart/form-data
            response = requests.post(url=self._base_url(endpoint),
                                     data=json_data,
                                     files=files)

        if response.status_code != 200:
            raise Exception(
                "%i: %s -> Unable to call %s. JSON Data: %s, Files: %s" % (
                    int(response.status_code),
                    response.reason,
                    self._base_url(
                        endpoint,
                        hide_token=True),  # do not log the token value
                    repr(json_data),
                    str(files)[:50]))

    def _send_message(self, text):
        self._api_command(
            "sendMessage", **{
                "text": text,
                "disable_web_page_preview": True,
                "parse_mode": "html"
            })

    def _send_photo(self, caption, photo_data):
        self._api_command("sendPhoto",
                           files={"photo": photo_data},
                           **{
                               "parse_mode": "html",
                               "caption": caption
                           })

    def _send_mediagroup(self, photo_data, media_description):
        """
        Send multiple media to telegram as one album.
        photo_data => a key-value mapping in the format 'filename': 'image data'
        media_description => a list of dicts telling telegram, what images are in photo_data

        https://core.telegram.org/bots/api#sendmediagroup
        https://core.telegram.org/bots/api#inputmediaphoto
        https://github.com/php-telegram-bot/core/issues/811
        """

        self._api_command("sendMediaGroup",
                           files=photo_data,
                           **{
                               "disable_notification": True,
                               "media": json.dumps(media_description)
                           })

    # TODO: refactor
    def notify(self):
        text = self.__config.notification_content()

        try:
            # TODO: this could all be put directly into "performance_graphs" function of config
            # which would return an empty list when graphs should not be sent
            if self.__config.should_send_graph():
                # fetch images
                attachments, _ = self.__config.performance_graphs
            else:
                attachments = []

            if len(attachments
                ) == 1:  # exactly one picture, send as photo with caption
                _, _, att_data, _ = attachments[0]
                self._send_photo(text, att_data)

            elif len(attachments) > 1:  # more than one picture, send as album
                telegram_media = []  # media description list for telegram API
                media_data = {}  # the actual image data
                for _, att_name, att_data, _ in attachments:
                    telegram_media.append({
                        "type": "photo",
                        "media": "attach://%s" % att_name
                    })

                    media_data[att_name] = att_data

                # Add notification text as description
                telegram_media[-1].update({"caption": text, "parse_mode": "html"})

                self._send_mediagroup(media_data, telegram_media)
            else:  # no pictures, send text only
                self._send_message(text)

        except AttributeError as atterr:
            stderr.write(repr(atterr))
            s_exit(2)

TelegramNotifier(TelegramConfig()).notify()