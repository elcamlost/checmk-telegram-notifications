# Project: Checkmk Telegram Notification Plugin

A Checkmk 2.3+ MKP package that sends monitoring notifications to Telegram.

## Structure

- `notifications/telegram` — the notification script (no `.py` extension, executable)
- `cmk_addons_plugins/telegram_notify/rulesets/notification_parameters.py` — form spec using `cmk.rulesets.v1` (Checkmk 2.4 new API)
- `package.py` — builds the `.mkp` archive
- `tests/` — pytest unit tests (no Checkmk required)
- `test.py` — manual end-to-end test (sends a real notification)
- `pyproject.toml` — dev dependencies (`pytest`, `pytest-cov`, `ruff`)

## Key technical facts

### Notification script
- Named `telegram` (no extension) so Checkmk identifies it as method `telegram`
- Uses `subprocess` to call `curl` for all Telegram API requests — no Python HTTP library dependencies
- SOCKS5 proxy support via `--proxy socks5h://` and `--proxy-user` curl args (credentials passed separately to avoid URL encoding issues)
- Bot token and proxy password extracted with `utils.get_password_from_env_or_context()` to support both explicit passwords and Checkmk password store references

### Form spec (Checkmk 2.4 new API)
- Uses `cmk.rulesets.v1.rule_specs.NotificationParameters` with `name="telegram"` and `topic=Topic.NOTIFICATIONS`
- Dictionary keys must be valid Python identifiers — graph config uses `ok/warn/crit/unknown` (not `0/1/2/3`)
- Discovered via `rule_spec_*` variable naming convention

### Password handling (Checkmk 2.4)
- New API stores passwords as `('cmk_postprocessed', 'explicit_password', ('uuid', 'value'))` or `('cmk_postprocessed', 'stored_password', ('store_id', ''))`
- `add_to_event_context` explodes tuples into indexed env vars (`_1`, `_2`, `_3_2`)
- `utils.get_password_from_env_or_context(key, context)` collects all matching keys and calls `retrieve_from_passwordstore` which handles both formats

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install ".[dev]"
.venv/bin/pytest -v
```

The test suite mocks `cmk.notification_plugins.utils` via `sys.modules` in `tests/conftest.py`. When adding new utils calls, add corresponding mock setup there.

## Deployment

```bash
python3 package.py
mkp install telegram_notify.mkp   # on the Checkmk server
```

After installing a new version, reload the Checkmk site so the new form spec is picked up.
