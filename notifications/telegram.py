#!/usr/bin/env python3
# Telegram

import base64
import os
import json
import requests
from sys import stderr, exit as s_exit
from urllib.parse import quote
from urllib.request import urlopen
from cmk.notification_plugins import utils
from cmk.notification_plugins.mail import event_templates
import cmk.utils.site as site

# TODO: Add logging to allow better troubleshooting of issues?

TELEGRAM_SAFE_MAX_CAPTION_LENGTH = 800


def is_service_notification(context):
    return context["WHAT"] == "SERVICE"


class GraphFetcher():
    def __init__(self, context):
        self.hostname = context["HOSTNAME"]

        if is_service_notification(context):
            self.svc_desc = context["SERVICEDESC"]
        else:
            self.svc_desc = "_HOST_"

    def render_performance_graphs(self):
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
        except Exception as e:
            stderr.write("ERROR: Failed to fetch graphs: %s\nURL: %s\n" %
                         (e, url))
            return []

        attachments = []
        for i, base64_source in enumerate(json_data):
            filename = '%s-%s-%d.png' % (self.hostname, self.svc_desc, i)
            attachments.append((filename, base64.b64decode(base64_source)))

        return attachments


class TelegramConfig():
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

        # NOTE: There is utils.html_escape_context. Since we need HTML tags in the templates, we may not use it, though.
        output = "%sOUTPUT" % self.__context["WHAT"]
        long_output = "LONG%sOUTPUT" % self.__context["WHAT"]
        for search, replace in [("<", "&lt;"), (">", "&gt;")]:
            self.__context[output] = self.__context[output].replace(
                search, replace)
            self.__context[long_output] = self.__context[long_output].replace(
                search, replace)

    def _limit_message_length(self, template_text):
        "Telegram supports at most 1024 characters for media captions. This function will cut overly long output information"

        # FIXME: It would be better to parse the template into an object using context-senstive language parsing (HTML?) and handling each information on its own.
        # E.g. handle whole HTML blocks of information (to not loose the end tag when cutting) and to allow more accurate length limitations.
        # THis could be done by HTML parsing the template and iterating over any nodes that are found. Each node should then be processed line by line.
        # Then, each single variable could be replaced one by one. Like this we could accurately determine the total message length. This in turn allows us to 
        # precisely cut HTML nodes without potentialls losing their end tags.

        what = lambda p: p % self.__context["WHAT"]

        output = self.__context[what("%sOUTPUT")]
        long_output = self.__context[what("LONG%sOUTPUT")]

        template_length = len(template_text) * 2 # NOTE: This is just an approximation; most of the template _should_ be variables that get replaced
        output_length = len(output)
        long_output_length = len(long_output)

        total_length = template_length + output_length + long_output_length

        if total_length > TELEGRAM_SAFE_MAX_CAPTION_LENGTH: # NOTE: official max is 1024. Since we are approximating here we should allow some spare space, though
            diff = total_length - TELEGRAM_SAFE_MAX_CAPTION_LENGTH

            if long_output_length:
                self.__context[what("LONG%sOUTPUT")] = "-CUT-" # we could just cut to the length we need. However, this way it is easier to handle
                diff = diff - long_output_length + 5

            if diff > 0: # Cutting long output did not suffice...
                if output_length >= diff:
                    self.__context[what("%sOUTPUT")] = output[:output_length - diff]
                    diff = 0
                elif output_length:
                    self.__context[what("%sOUTPUT")] = "-CUT-"
                    diff = diff - output_length + 5

                    if diff - output_length + 5 > 0: # The message is STILL too long. Overwrite the template...
                        return "There is an issue on $LINKEDHOSTNAME$. However, the notification would be too long to display and has been cut."

        return template_text

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
    def performance_graphs(self):
        if self._should_send_graphs:
            return GraphFetcher(self.__context).render_performance_graphs()
        return []

    @property
    def bot_token(self):
        if not self.__bot_token:
            if self.bot_token_field_name in self.__context:
                self.__bot_token = self.__context[self.bot_token_field_name]
                return utils.retrieve_from_passwordstore(self.__bot_token)
            raise AttributeError("Unable to find context variable '%s'" %
                                 self.bot_token_field_name)
        return self.__bot_token

    @property
    def chat_id(self):
        if not self.__chat_id:
            for fieldname in self.chat_id_field_names:
                if fieldname in self.__context and self.__context[
                        fieldname] != 0:
                    self.__chat_id = self.__context[fieldname]
                    return self.__chat_id
            raise AttributeError("Unable to find chat ID in any field: %s" %
                                 ",".join(self.chat_id_field_names))
        return self.__chat_id

    @property
    def notification_content(self):
        if is_service_notification(self.__context):
            template = self.__context.setdefault(self.service_template_field_name,
                                             self.default_service_template)
        else:
            template = self.__context.setdefault(self.host_template_field_name,
                                             self.default_host_template)

        template = self._limit_message_length(template)
        text = utils.substitute_context(template, self.__context)

        return text.replace("\\n", "\n")


class TelegramNotifier():
    def __init__(self, config):
        self.__config = config

    def _base_url(self, endpoint, hide_token=False):
        return "https://api.telegram.org/bot%s/%s" % (
            self.__config.bot_token if not hide_token else "****", endpoint)

    def _api_command(self, endpoint, files=None, **kwargs):
        # NOTE: There is utils.post_request. However, this function assumes that context is not modified before submission. Thus, we may not use it.
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
                              "caption": caption # FIXME: Max length for captions is 1024. Since we rely on templating and checkmk built-in functions, this may not be easily handled, though. Have a look at _limit_message_length
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

    def notify(self):
        text = self.__config.notification_content

        try:
            attachments = self.__config.performance_graphs

            if len(attachments
                   ) == 1:  # exactly one picture, send as photo with caption
                _, att_data = attachments[0]
                self._send_photo(text, att_data)

            elif len(attachments) > 1:  # more than one picture, send as album
                telegram_media = []  # media description list for telegram API
                media_data = {}  # the actual image data
                for att_name, att_data in attachments:
                    telegram_media.append({
                        "type": "photo",
                        "media": "attach://%s" % att_name
                    })

                    media_data[att_name] = att_data

                # Add notification text as description
                telegram_media[-1].update({
                    "caption": text,
                    "parse_mode": "html"
                })

                self._send_mediagroup(media_data, telegram_media)
            else:  # no pictures, send text only
                self._send_message(text)

        except AttributeError as atterr:
            stderr.write(repr(atterr))
            s_exit(2)


TelegramNotifier(TelegramConfig()).notify()
