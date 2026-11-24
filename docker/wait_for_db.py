"""等待 PostgreSQL 可连接，供容器启动脚本调用。"""

import os
import sys
import time

import psycopg

retries = int(os.environ.get("WAIT_FOR_DB_RETRIES", "30"))
delay = float(os.environ.get("WAIT_FOR_DB_DELAY", "2"))

params = {
    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
    "port": os.environ.get("POSTGRES_PORT", "5432"),
    "dbname": os.environ.get("POSTGRES_DB", "fund_pooling"),
    "user": os.environ.get("POSTGRES_USER", "fund_pooling"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
    "connect_timeout": 3,
}


def main() -> int:
    """反复尝试连接数据库，成功返回 0，重试耗尽返回 1。"""
    for attempt in range(1, retries + 1):
        try:
            with psycopg.connect(**params):
                print(f"[wait_for_db] 数据库已就绪（第 {attempt} 次尝试）", flush=True)
                return 0
        except Exception as exc:  # noqa: BLE001
            print(f"[wait_for_db] 第 {attempt}/{retries} 次连接失败：{exc}", flush=True)
            time.sleep(delay)

    print("[wait_for_db] 数据库始终不可用，放弃等待", file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
