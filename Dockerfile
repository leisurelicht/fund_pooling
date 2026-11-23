# syntax=docker/dockerfile:1.7

# =============================================================================
# Stage 1：构建 Vue 3 前端
# =============================================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

# 先复制依赖清单，最大化利用构建缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# 生产环境下静态资源由 Django 在 /static/ 前缀下提供
ENV VITE_BASE=/static/
RUN npm run build

# =============================================================================
# Stage 2：使用 uv 安装 Python 依赖
# =============================================================================
FROM ghcr.io/astral-sh/uv:0.13.9 AS uv

FROM python:3.13-slim-bookworm AS python-builder

COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# 仅依赖文件变化时才重新解析依赖
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# =============================================================================
# Stage 3：运行时镜像（Gunicorn + WhiteNoise + 前端静态资源）
# =============================================================================
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=8000

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app
# Gunicorn 需要在 /app 下创建控制 socket 目录，因此目录本身要归 app 用户
RUN chown app:app /app

COPY --from=python-builder --chown=app:app /app /app

# 前端构建产物作为静态源目录，collectstatic 复制进 staticfiles 并生成 gzip 压缩版本
COPY --from=frontend-builder --chown=app:app /app/frontend/dist/ /app/frontend-dist/
RUN STATICFILES_DIRS=/app/frontend-dist python manage.py collectstatic --noinput \
    && rm -rf /app/frontend-dist \
    && chown -R app:app /app/staticfiles

COPY --chown=app:app docker/entrypoint.sh /app/entrypoint.sh
COPY --chown=app:app docker/wait_for_db.py /app/docker/wait_for_db.py
RUN chmod 755 /app/entrypoint.sh

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=3)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "-c", "gunicorn.conf.py"]
