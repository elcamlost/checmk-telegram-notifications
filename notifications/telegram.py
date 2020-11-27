#!/usr/bin/env python3
# Telegram

import os
import json
import requests
from sys import stderr, exit as s_exit

from cmk.notification_plugins import utils
from cmk.notification_plugins.mail import render_performance_graphs

CHAT_ID_FIELD_NAMES = [
    "PARAMETER_TELEGRAM_CHAT_ID", # for notification parameters
    "CONTACT_TELEGRAM_CHAT_ID" # for custom attributes
]
BOT_TOKEN_FIELD = "PARAMETER_TELEGRAM_BOT_TOKEN"

# TODO: stop linking hostname/service descr?
HOST_TEMPLATE = """<b>Check_MK: <a href="%s">$HOSTNAME$ - $EVENT_TXT$</a></b>
<code>
Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$

$LONGHOSTOUTPUT$</code>"""

# TODO: add parameter to define URL prefix like for mail

SERVICE_TEMPLATE = """<b>Check_MK: <a href="%s">$HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$</a></b>
<code>
Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$

$LONGSERVICEOUTPUT$</code>"""

def telegram_bot_token(context):
    if BOT_TOKEN_FIELD in context:
        return context[BOT_TOKEN_FIELD]
    raise AttributeError("Unable to find context variable '%s'" % BOT_TOKEN_FIELD)

def telegram_chat_id(context):
    for fieldname in CHAT_ID_FIELD_NAMES:
        if fieldname in context and context[fieldname] != 0:
            return context[fieldname]
    raise AttributeError("Unable to find chat ID in any field: %s" % ",".join(CHAT_ID_FIELD_NAMES))

def telegram_url_for(command, context, hide_token=False):
    return "https://api.telegram.org/bot%s/%s" % (telegram_bot_token(context) if not hide_token else "****", command)

def telegram_command(endpoint, context, files=None, **kwargs):
    json_data = dict({
        "chat_id": telegram_chat_id(context)
    }, **kwargs)

    if not files:
        response = requests.post(
            url=telegram_url_for(endpoint, context),
            json=json_data,
            files=files
        )
    else: # when sending files we need to also send parameters using multipart/form-data
        # stderr.write(repr(requests.Request("POST", telegram_url_for(endpoint, context), files=files).prepare().body.decode("ascii")))
        response = requests.post(
            url=telegram_url_for(endpoint, context),
            data=json_data,
            files=files
        )
    
    if response.status_code != 200:
        raise Exception("%i: %s -> Unable to call %s. JSON Data: %s, Files: %s" % (
                int(response.status_code),
                response.reason,
                telegram_url_for(endpoint, context, hide_token=True), # do not log the token value
                repr(json_data),
                str(files)[:50]
            ))

def telegram_send_message(context, text):
    telegram_command("sendMessage", context, **{
            "text": text,
            "disable_web_page_preview": True,
            "parse_mode": "html"
        })

def telegram_send_photo(context, caption, photo_data):
    telegram_command("sendPhoto", context, files={"photo": photo_data}, **{
        "parse_mode": "html",
        "caption": caption
    })

def telegram_send_mediagroup(context, photo_data, media_description):
    """
    Send multiple media to telegram as one album.
    photo_data => a key-value mapping in the format 'filename': 'image data'
    media_description => a list of dicts telling telegram, what images are in photo_data

    https://core.telegram.org/bots/api#sendmediagroup
    https://core.telegram.org/bots/api#inputmediaphoto
    https://github.com/php-telegram-bot/core/issues/811
    """

    telegram_command("sendMediaGroup", context, files=photo_data, **{
        "disable_notification": True,
        "media": json.dumps(media_description)
        # "media": [ { "type": "photo", "media": "attach://photo_1" }, ... ]
        # --- from files parameter:
        # "photo_1": binary data
        # "photo_2": binary data
    })

def main(host_template, service_template):
    context = utils.collect_context()

    if context["WHAT"] == "SERVICE":
        text = service_template % utils.service_url_from_context(context)
    else:
        text = host_template % utils.host_url_from_context(context)
    text = utils.substitute_context(text, context)

    try:
        # fetch images
        attachments, _ = render_performance_graphs(context)

        if len(attachments) == 1: # exactly one picture, send as photo with caption
            _, _, att_data, _ = attachments[0]
            telegram_send_photo(context, text, att_data)

        elif len(attachments) > 1: # more than one picture, send as album
            telegram_media = [] # media description list for telegram API
            media_data = {} # the actual image data
            for _, att_name, att_data, _ in attachments:
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

            telegram_send_mediagroup(context, media_data, telegram_media)
        else: # no pictures, send text only
            telegram_send_message(context, text)

    except AttributeError as atterr:
        stderr.write(repr(atterr))
        s_exit(2)

main(HOST_TEMPLATE, SERVICE_TEMPLATE)
