"""Gunicorn 配置（通过环境变量调整）。

docker compose 中的 CMD 为：gunicorn config.wsgi:application -c gunicorn.conf.py

说明：Gunicorn 要求配置项以**模块级小写变量**暴露（`bind`、`workers` 等），
直接写小写模块变量会被 IDE 判定为「常量未用 UPPER_CASE 命名」。
因此这里在函数内计算配置，再注入模块命名空间，保持 Gunicorn 约定不变。
"""

import multiprocessing
import os


def _int_env(name: str, default: int) -> int:
    """读取整型环境变量，非法值回退到默认值。"""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _build_config() -> dict[str, object]:
    """按环境变量计算 Gunicorn 配置。"""
    return {
        "bind": f"0.0.0.0:{os.environ.get('PORT', '8000')}",
        # 默认按 CPU 数计算，但上限 9，避免在开发机 / 小服务器上起过多 worker
        "workers": _int_env("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 9)),
        "threads": _int_env("GUNICORN_THREADS", 2),
        "worker_class": "gthread",
        "timeout": _int_env("GUNICORN_TIMEOUT", 60),
        "graceful_timeout": 30,
        "keepalive": 5,
        "max_requests": _int_env("GUNICORN_MAX_REQUESTS", 1000),
        "max_requests_jitter": 100,
        "accesslog": "-",
        "errorlog": "-",
        "loglevel": os.environ.get("GUNICORN_LOG_LEVEL", "info").lower(),
        "forwarded_allow_ips": "*",
    }


globals().update(_build_config())
