#!/usr/bin/env python3
try:
    from cmk.discover_plugins import discover_all_plugins
except ImportError:
    from cmk.discover_plugins import discover_plugins as discover_all_plugins
import inspect

from cmk.discover_plugins import PluginGroup
from cmk.rulesets.v1 import entry_point_prefixes

kwargs = {"raise_errors": False}
if "skip_wrong_types" in inspect.signature(discover_all_plugins).parameters:
    kwargs["skip_wrong_types"] = True

result = discover_all_plugins(PluginGroup.RULESETS, entry_point_prefixes(), **kwargs)

errors = [str(e) for e in result.errors if "telegram_notify" in str(e)]
for e in errors:
    print("ERROR:", e)

found = [loc.module for loc in result.plugins if "telegram_notify" in loc.module]
for f in found:
    print("Found:", f)

assert not errors, f"Plugin has {len(errors)} error(s)"
assert found, "telegram_notify not found in discovered plugins"
print("OK")
