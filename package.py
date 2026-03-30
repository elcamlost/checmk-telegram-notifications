#!/usr/bin/env python3

import io
import json
import shutil
import tarfile
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent

PKG_NAME = "telegram_notify"
TITLE = "Telegram notification plugin"
AUTHOR = "Ilya Rassadin elcamlost at gmail dot com"
DESCRIPTION = "Send monitoring notifications to a configurable Telegram bot."
DOWNLOAD_URL = "https://github.com/elcamlost/checkmk_notify_telegram"
PLUGIN_VERSION = "2.0.0"
CHECKMK_MIN_VERSION = "2.3.0"


def build_staging(source: Path, staging: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(source / "notifications", staging / "notifications", ignore=ignore)
    shutil.copytree(source / "cmk_addons_plugins", staging / "cmk_addons_plugins", ignore=ignore)


def make_category_tar(category_dir: Path) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", dereference=True) as tar:
        for path in sorted(category_dir.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=str(path.relative_to(category_dir)))
    return category_dir.name, buf.getvalue()


def collect_files(staging: Path) -> dict[str, list[str]]:
    files = {}
    for category_dir in sorted(p for p in staging.iterdir() if p.is_dir()):
        files[category_dir.name] = sorted(
            str(p.relative_to(category_dir)) for p in category_dir.rglob("*") if p.is_file()
        )
    return files


def build_info(files: dict[str, list[str]]) -> dict:
    return {
        "author": AUTHOR,
        "description": DESCRIPTION,
        "download_url": DOWNLOAD_URL,
        "files": files,
        "name": PKG_NAME,
        "num_files": sum(len(v) for v in files.values()),
        "title": TITLE,
        "version": PLUGIN_VERSION,
        "version.min_required": CHECKMK_MIN_VERSION,
        "version.packaged": CHECKMK_MIN_VERSION,
        "version.usable_until": None,
    }


def build_mkp(output: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        build_staging(REPO_ROOT, staging)

        files = collect_files(staging)
        info = build_info(files)
        categories = [make_category_tar(d) for d in sorted(staging.iterdir()) if d.is_dir()]

        with tarfile.open(output, "w:gz") as mkp:
            for name, data in categories:
                ti = tarfile.TarInfo(name=f"{name}.tar")
                ti.size = len(data)
                mkp.addfile(ti, io.BytesIO(data))

            for filename, content in (
                ("info", repr(info).encode()),
                ("info.json", json.dumps(info).encode()),
            ):
                ti = tarfile.TarInfo(name=filename)
                ti.size = len(content)
                mkp.addfile(ti, io.BytesIO(content))


if __name__ == "__main__":
    output = REPO_ROOT / f"{PKG_NAME}.mkp"
    build_mkp(output)
    print(f"Built {output}")
