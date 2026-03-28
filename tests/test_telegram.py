import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load the notification script (no .py extension — must provide loader explicitly)
_path = str(Path(__file__).parent.parent / "notifications" / "telegram")
_loader = SourceFileLoader("telegram_plugin", _path)
_spec = importlib.util.spec_from_file_location("telegram_plugin", _path, loader=_loader)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

TelegramMessage = _module.TelegramMessage
TelegramConfig = _module.TelegramConfig
TelegramNotifier = _module.TelegramNotifier
TELEGRAM_MESSAGE_LEN_LIMIT = _module.TELEGRAM_MESSAGE_LEN_LIMIT

from tests.conftest import mock_utils  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONTEXT = {
    "NOTIFICATIONTYPE": "PROBLEM",
    "WHAT": "SERVICE",
    "SERVICESTATEID": "2",
    "PREVIOUSSERVICEHARDSHORTSTATE": "OK",
    "SERVICESHORTSTATE": "CRIT",
    "HOSTNAME": "testhost",
    "HOSTALIAS": "testalias",
    "HOSTADDRESS": "1.2.3.4",
    "SERVICEDESC": "testservice",
    "SERVICEOUTPUT": "",
    "LONGSERVICEOUTPUT": "",
}


def make_config(extra=None):
    """Instantiate TelegramConfig with a controlled context."""
    ctx = {**MINIMAL_CONTEXT, **(extra or {})}
    mock_utils.collect_context.return_value = ctx
    return TelegramConfig()


def make_notifier(chat_id="123456789", bot_token="1234:token", proxy_args=None):
    """Instantiate TelegramNotifier with a mocked config."""
    config = MagicMock(spec=TelegramConfig)
    config.chat_id = chat_id
    config.bot_token = bot_token
    config.proxy_args = proxy_args or []
    return TelegramNotifier(config)


# ---------------------------------------------------------------------------
# TelegramMessage — truncation logic
# ---------------------------------------------------------------------------


class TestTelegramMessage:
    def _make(self, long_output="", output=""):
        ctx = {
            "WHAT": "SERVICE",
            "LONGSERVICEOUTPUT": long_output,
            "SERVICEOUTPUT": output,
        }
        template = "$LONGSERVICEOUTPUT$$SERVICEOUTPUT$"
        return TelegramMessage(template=template, context=ctx)

    def test_short_message_unchanged(self):
        msg = self._make(long_output="short")
        assert msg.content == "short"

    def test_message_at_limit_unchanged(self):
        text = "x" * TELEGRAM_MESSAGE_LEN_LIMIT
        ctx = {"WHAT": "SERVICE", "LONGSERVICEOUTPUT": text, "SERVICEOUTPUT": ""}
        m = TelegramMessage(template="$LONGSERVICEOUTPUT$$SERVICEOUTPUT$", context=ctx)
        assert len(m.content) == TELEGRAM_MESSAGE_LEN_LIMIT

    def test_long_output_truncated_first(self):
        long = "L" * (TELEGRAM_MESSAGE_LEN_LIMIT + 100)
        ctx = {"WHAT": "SERVICE", "LONGSERVICEOUTPUT": long, "SERVICEOUTPUT": "short"}
        m = TelegramMessage(template="$LONGSERVICEOUTPUT$$SERVICEOUTPUT$", context=ctx)
        assert len(m.content) <= TELEGRAM_MESSAGE_LEN_LIMIT
        assert "short" in m.content

    def test_long_output_dropped_when_still_too_long(self):
        # output alone already exceeds the limit
        output = "O" * (TELEGRAM_MESSAGE_LEN_LIMIT + 10)
        long = "L" * 100
        ctx = {"WHAT": "SERVICE", "LONGSERVICEOUTPUT": long, "SERVICEOUTPUT": output}
        m = TelegramMessage(template="$LONGSERVICEOUTPUT$$SERVICEOUTPUT$", context=ctx)
        assert len(m.content) <= TELEGRAM_MESSAGE_LEN_LIMIT
        # long output was dropped
        assert "L" not in m.content

    def test_result_cached(self):
        msg = self._make(long_output="hello")
        first = msg.content
        second = msg.content
        assert first is second


# ---------------------------------------------------------------------------
# TelegramConfig — proxy_args
# ---------------------------------------------------------------------------


class TestProxyArgs:
    def test_no_proxy_returns_empty(self):
        cfg = make_config()
        assert cfg.proxy_args == []

    def test_proxy_server_only(self):
        cfg = make_config({"PARAMETER_TELEGRAM_SOCKS5_PROXY_SERVER": "proxy.example.com"})
        args = cfg.proxy_args
        assert "--proxy" in args
        assert "socks5h://proxy.example.com:1080" in args
        assert "--proxy-user" not in args

    def test_proxy_custom_port(self):
        cfg = make_config(
            {
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_SERVER": "proxy.example.com",
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_PORT": "1234",
            }
        )
        assert "socks5h://proxy.example.com:1234" in cfg.proxy_args

    def test_proxy_with_auth(self):
        mock_utils.get_password_from_env_or_context.return_value = "s3cr3t"
        cfg = make_config(
            {
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_SERVER": "proxy.example.com",
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_USER": "proxyuser",
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_PASSWORD_1": "cmk_postprocessed",
            }
        )
        args = cfg.proxy_args
        assert "--proxy-user" in args
        assert "proxyuser:s3cr3t" in args
        mock_utils.get_password_from_env_or_context.return_value = ""

    def test_proxy_with_special_chars_in_password(self):
        mock_utils.get_password_from_env_or_context.return_value = "p%ss!w@rd"
        cfg = make_config(
            {
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_SERVER": "proxy.example.com",
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_USER": "user",
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_PASSWORD_1": "cmk_postprocessed",
            }
        )
        args = cfg.proxy_args
        # password must be passed as-is, not URL-encoded
        assert "user:p%ss!w@rd" in args
        mock_utils.get_password_from_env_or_context.return_value = ""

    def test_user_without_password_omits_proxy_user(self):
        mock_utils.get_password_from_env_or_context.return_value = ""
        cfg = make_config(
            {
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_SERVER": "proxy.example.com",
                "PARAMETER_TELEGRAM_SOCKS5_PROXY_USER": "user",
            }
        )
        assert "--proxy-user" not in cfg.proxy_args


# ---------------------------------------------------------------------------
# TelegramNotifier — _api_command (curl invocation)
# ---------------------------------------------------------------------------


class TestApiCommand:
    def _run_result(self, body="", status=200, returncode=0):
        r = MagicMock()
        r.stdout = "%s\n%d" % (body, status)
        r.stderr = ""
        r.returncode = returncode
        return r

    def test_send_message_calls_curl_with_json(self):
        notifier = make_notifier()
        with patch("subprocess.run", return_value=self._run_result()) as mock_run:
            notifier._send_message("hello")
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "curl"
        assert "-H" in cmd
        assert "Content-Type: application/json" in cmd
        payload = json.loads(cmd[cmd.index("-d") + 1])
        assert payload["text"] == "hello"
        assert payload["chat_id"] == "123456789"
        assert payload["parse_mode"] == "html"

    def test_send_message_includes_proxy_args(self):
        notifier = make_notifier(proxy_args=["--proxy", "socks5h://p:1080", "--proxy-user", "u:pw"])
        with patch("subprocess.run", return_value=self._run_result()) as mock_run:
            notifier._send_message("hi")
        cmd = mock_run.call_args[0][0]
        assert "--proxy" in cmd
        assert "socks5h://p:1080" in cmd
        assert "--proxy-user" in cmd
        assert "u:pw" in cmd

    def test_400_response_exits_2(self):
        notifier = make_notifier()
        with patch("subprocess.run", return_value=self._run_result(status=400)):
            with pytest.raises(SystemExit) as exc:
                notifier._send_message("hi")
        assert exc.value.code == 2

    def test_500_response_exits_1(self):
        notifier = make_notifier()
        with patch("subprocess.run", return_value=self._run_result(status=500)):
            with pytest.raises(SystemExit) as exc:
                notifier._send_message("hi")
        assert exc.value.code == 1

    def test_curl_failure_exits_2(self):
        notifier = make_notifier()
        with patch("subprocess.run", return_value=self._run_result(returncode=7)):
            with pytest.raises(SystemExit) as exc:
                notifier._send_message("hi")
        assert exc.value.code == 2

    def test_200_response_does_not_exit(self):
        notifier = make_notifier()
        with patch("subprocess.run", return_value=self._run_result(status=200)):
            notifier._send_message("hi")  # must not raise


# ---------------------------------------------------------------------------
# TelegramConfig — event text generation
# ---------------------------------------------------------------------------


class TestExtendContext:
    def test_problem_event_txt(self):
        cfg = make_config()
        # PROBLEM: PREVIOUSSERVICEHARDSHORTSTATE -> SERVICESHORTSTATE
        assert "OK" in cfg.notification_content
        assert "CRIT" in cfg.notification_content

    def test_flap_start_event_txt(self):
        cfg = make_config({"NOTIFICATIONTYPE": "FLAPPINGSTART"})
        assert "Flapping" in cfg.notification_content

    def test_downtime_event_txt(self):
        cfg = make_config(
            {
                "NOTIFICATIONTYPE": "DOWNTIMESTART",
                "SERVICESHORTSTATE": "OK",
                "SERVICESTATEID": "0",
            }
        )
        assert "Downtime" in cfg.notification_content

    def test_acknowledgement_event_txt(self):
        cfg = make_config({"NOTIFICATIONTYPE": "ACKNOWLEDGEMENT"})
        assert "Acknowledged" in cfg.notification_content


# ---------------------------------------------------------------------------
# TelegramConfig — HTML escaping
# ---------------------------------------------------------------------------


class TestEscapeHtmlOutput:
    def test_lt_gt_escaped_in_output(self):
        cfg = make_config({"SERVICEOUTPUT": "value <3 > 0"})
        assert "&lt;" in cfg.notification_content
        assert "&gt;" in cfg.notification_content
        assert "<3" not in cfg.notification_content

    def test_lt_gt_escaped_in_long_output(self):
        cfg = make_config({"LONGSERVICEOUTPUT": "detail <ok>"})
        assert "&lt;" in cfg.notification_content
        assert "&gt;" in cfg.notification_content
