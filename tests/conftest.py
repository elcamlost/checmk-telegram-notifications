"""
Mock the cmk module so tests can run without a Checkmk installation.
"""

import sys
from unittest.mock import MagicMock


def _substitute_context(template, context):
    result = template
    for key, value in context.items():
        result = result.replace("$%s$" % key, str(value))
    return result


def _format_link(fmt, url, text):
    return fmt % (url, text) if url else text


mock_utils = MagicMock()
mock_utils.substitute_context.side_effect = _substitute_context
mock_utils.format_link.side_effect = _format_link
mock_utils.host_url_from_context.return_value = ""
mock_utils.service_url_from_context.return_value = ""
mock_utils.collect_context.return_value = {}
mock_utils.get_password_from_env_or_context.return_value = ""

cmk_notification_plugins = MagicMock()
cmk_notification_plugins.utils = mock_utils

sys.modules["cmk"] = MagicMock()
sys.modules["cmk.notification_plugins"] = cmk_notification_plugins
sys.modules["cmk.notification_plugins.utils"] = mock_utils
