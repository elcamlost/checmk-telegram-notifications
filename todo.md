# TODO

from mail import event_template


event_template_txt, event_template_html = event_templates(context["NOTIFICATIONTYPE"])
context["EVENT_TXT"] = utils.substitute_context(
    event_template_txt.replace("@", context["WHAT"]), context)
context["EVENT_HTML"] = utils.substitute_context(
    event_template_html.replace("@", context["WHAT"]), context)