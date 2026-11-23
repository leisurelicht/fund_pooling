#!/bin/sh
# 容器启动脚本：等待数据库 → 执行迁移 → 可选创建超级用户 → 启动 Gunicorn
set -eu

echo "[entrypoint] $(date '+%Y-%m-%d %H:%M:%S') 启动 fund_pooling web 容器"

if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
    python /app/docker/wait_for_db.py
fi

echo "[entrypoint] 执行数据库迁移 ..."
python manage.py migrate --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "[entrypoint] 创建/更新超级用户 ${DJANGO_SUPERUSER_USERNAME} ..."
    python manage.py createsuperuser --noinput || echo "[entrypoint] 超级用户已存在，跳过"
fi

echo "[entrypoint] 启动应用：$*"
exec "$@"
