#!/usr/bin/env python
"""Django 命令行入口。"""

import os
import sys


def main() -> None:
    """Django 命令行入口。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line  # noqa: PLC0415  # pylint: disable=import-outside-toplevel
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "无法导入 Django，请确认已执行 `uv sync`，并通过 `uv run` 运行本脚本。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
