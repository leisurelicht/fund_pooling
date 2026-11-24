# fund_pooling — Agent 指南

Django 6.1 + DRF + Vue 3 + Vite 8 + TypeScript + PostgreSQL 17 全栈项目。
uv 管理 Python 依赖，Docker Compose 编排两个镜像（`postgres:17-alpine` + `fund_pooling/web`）。

## 架构速览

```
浏览器 :8000 → web 容器（Gunicorn + Django + WhiteNoise + Vue SPA）
                   │ compose 内网 :5432
                   ▼
              db 容器（PostgreSQL，数据在宿主机 ./database/pgdata）
```

- 前后端**同容器同端口**：前端产物打进 `staticfiles/`，Django 以 `/static/` 提供
- `/api/*` → DRF 接口    `/admin/*` → Django Admin    其余路径 → SPA 兜底
- 登录：Django Session + `EmailOrUsernameBackend`（用户名或邮箱，邮箱大小写不敏感）
- CSRF：登录页自动下发 csrftoken，`client.ts` 自动带 `X-CSRFToken`

## 目录结构

```
fund_pooling/
├── Dockerfile                 # 三阶段构建（前端 → uv 依赖 → slim 运行时）
├── docker/                    # entrypoint.sh、wait_for_db.py
├── docker-compose.yml         # 本地开发编排
├── docker-compose.prod.yml    # 生产覆盖（127.0.0.1、无 5432 暴露、资源限制）
├── Makefile                   # 常用命令
├── deploy/                    # DEPLOY.md、deploy.sh、Caddyfile、nginx.conf
├── .env / .env.example        # 环境变量（PGDATA_HOST_PATH、BACKUP_HOST_PATH 等）
├── backend/
│   ├── config/                # settings.py / urls.py / wsgi.py / asgi.py
│   ├── apps/core/             # 核心 app：健康检查、登录、SPA 入口
│   │   ├── views.py           # 接口逻辑
│   │   ├── urls.py            # 路由（app_name="core"，挂载到 /api/ 下）
│   │   ├── auth_backends.py   # EmailOrUsernameBackend（用户名或邮箱登录）
│   │   ├── tests.py           # 16 个测试
│   │   └── models.py          # 暂无业务模型（后续在此或在新建 app 中添加）
│   ├── gunicorn.conf.py       # Gunicorn 配置（函数内计算 + globals().update）
│   ├── manage.py
│   ├── pyproject.toml         # uv 依赖 + ruff 规则
│   └── uv.lock
├── frontend/
│   ├── src/
│   │   ├── api/               # client.ts（fetch 封装、CSRF、错误处理）、auth.ts、system.ts
│   │   ├── auth/session.ts    # 登录状态管理（reactive，无需 Pinia）
│   │   ├── router/index.ts    # vue-router + beforeEach 登录守卫
│   │   ├── views/             # LoginView.vue、HomeView.vue
│   │   ├── components/        # StatusCard.vue
│   │   ├── App.vue / main.ts / style.css
│   │   └── ...
│   ├── package.json / vite.config.ts / tsconfig*.json
│   └── dist/                  # Vite 构建产物（gitignore）
└── database/                  # 本地 PG 数据（gitignore，绝不提交）
```

## 常用命令

| 命令 | 说明 |
| --- | --- |
| `make up` / `make down` | 启动 / 停止（自动 migrate） |
| `make ps` / `make logs` | 容器状态 / 日志 |
| `make test` | 容器内 Django 测试（`manage.py test`） |
| `make lint` | 后端 ruff + 前端 vue-tsc |
| `make format` | ruff format |
| `make superuser` | 创建 Django 管理员 |
| `make backup` / `make restore FILE=...` | 备份到 BACKUP_HOST_PATH / 恢复 |
| `make dev-db` / `make dev-backend` / `make dev-frontend` | 本地三件套（db 容器，Django 和 Vite 跑宿主机） |
| `make deploy` | 生产部署（db 无端口暴露，web 仅 127.0.0.1） |

## 编码约定

### Python（Django）

- **命名**：ruff 规则 `E, F, I, N, D1, UP, B, DJ`。docstring 必备，命名 snake_case
- **Django 特例**：`app_name`、`urlpatterns` 必须保持小写（`# pylint: disable=invalid-name`）
- **未使用参数**：`_request` 前缀（框架签名要求但方法体不用）
- **异常**：数据库层用 `DatabaseError`，不裸 `except Exception`
- **测试**：`apps/core/tests.py`，类按功能分组，`setUp` 创建共享测试数据
- **自定义后端**：`self.user_can_authenticate(user)` 检查 `is_active`

### TypeScript（Vue）

- **组件**：`<script setup lang="ts">`，组合式 API
- **路由**：`router/index.ts` — `public: true` meta 放行未登录页；登录守卫调 `loadSession()` 
- **状态**：`auth/session.ts` 是 reactive 单例，`loadSession()` → `/auth/me/` 判断登录态
- **API 请求**：`api/client.ts` 统一封装，POST 自动带 `X-CSRFToken`，`credentials: 'same-origin'`

### Docker

- 两个容器：`fund_pooling_db`（postgres:17-alpine）+ `fund_pooling_web`（自建镜像）
- web 镜像三阶段：`node:22-alpine` 构建前端 → `uv sync` 装依赖 → `python:3.13-slim-bookworm` 运行
- Gunicorn worker 上限 9；`entrypoint.sh` 等数据库后自动 migrate
- 生产覆盖用 `docker compose -f docker-compose.yml -f docker-compose.prod.yml`

## 常见任务

### 新增后端接口

1. 在 `apps/core/views.py` 加 `APIView` 子类（或新建 app）
2. 在 `apps/core/urls.py` 加路由
3. 如需鉴权：`permission_classes = [IsAuthenticated]`（全局默认 AllowAny，逐个设）
4. `make test` 补测试
5. `make lint` 通过

### 新增前端页面

1. `frontend/src/views/` 下新建 Vue 组件
2. `router/index.ts` 加路由（需登录则不加 `meta: { public: true }`）
3. `npm run build`（`frontend/` 下执行）

### 新增数据库模型

1. 在 `apps/core/models.py` 定义（或新建 app）
2. `make makemigrations` → `make migrate`
3. 序列化器 + 视图 + 路由

### 部署

```bash
make deploy              # 自动备份 → 构建 → 健康检查
make deploy ARGS="--pull"  # 从镜像仓库拉取
make deploy ARGS="--dry-run"  # 预览
```

生产编排额外做：web 仅监听 127.0.0.1、db 不暴露宿主机端口、resource limits、Gunicorn worker=3。