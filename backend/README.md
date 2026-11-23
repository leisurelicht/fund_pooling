# fund_pooling backend

Django + DRF 后端，使用 [uv](https://docs.astral.sh/uv/) 管理 Python 版本与依赖。

```bash
uv sync                  # 安装依赖（含 dev 依赖）
uv run python manage.py runserver   # 本地启动
uv run python manage.py migrate
uv run ruff check .
```

配置见项目根目录 `.env.example`。数据库连接默认指向 `127.0.0.1:5432`（本地开发），
容器内由 docker compose 覆盖为 `db:5432`。
