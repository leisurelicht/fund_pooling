# Fund Pooling · 基金管理平台

Django + Vue 3 + PostgreSQL 的全栈项目骨架，使用 **uv** 管理 Python 版本与依赖、
**Docker Compose** 编排两个独立镜像（数据库 / 服务）。
数据库文件存放在**本地 `./database`**，
`pg_dump` 备份写入宿主机上由 `BACKUP_HOST_PATH` 指定的目录。

- 后端：Django 6.1 + Django REST framework
- 前端：Vue 3 + Vite + TypeScript
- 数据库：PostgreSQL 17
- 依赖：uv（`pyproject.toml` + `uv.lock`）
- 部署：Docker + Docker Compose，`db` / `web` 两个镜像分离开

---

## 1. 架构

```
浏览器
  │  HTTP :8000
  ▼
┌──────────────────────────── web 容器（镜像 fund_pooling/web）────────────────────────────┐
│ Gunicorn（config.wsgi:application）                                                      │
│  ├── /            → Vue SPA（构建产物在 staticfiles，由 WhiteNoise 提供 /static/ 资源）    │
│  ├── /api/        → Django REST framework（/api/health/、/api/system/）                  │
│  ├── /admin/      → Django Admin                                                         │
│  └── /static/     → WhiteNoise（Vue 资源 + admin 静态文件）                               │
└───────────────────────────────────────┬──────────────────────────────────────────────────┘
                                        │  TCP 5432（compose 内部网络）
                                        ▼
┌───────────────────────── db 容器（官方镜像 postgres:17-alpine）──────────────────────────┐
│ /var/lib/postgresql/data/pgdata（容器唯一挂载点）                                        │
└───────────────────────────────────────┬──────────────────────────────────────────────────┘
                                        │ bind mount
                                        ▼
                        ./database/pgdata（本地磁盘，运行中的数据）

make backup（宿主机执行）── pg_dump 标准输出重定向 ──▶ $BACKUP_HOST_PATH（宿主机备份目录）
                            （容器不需要挂载备份目录，只存 .dump，可随时重建）
```

两个镜像分别构建、分别部署：

| 镜像 | 容器 | 说明 |
| --- | --- | --- |
| `postgres:17-alpine` | `fund_pooling_db` | 数据库，数据落在本地 `./database`，备份输出到宿主机备份目录 |
| `fund_pooling/web:0.1.0` | `fund_pooling_web` | 多阶段构建：Node 构建前端 → uv 安装依赖 → Python slim 运行 Gunicorn |

web 只在 db 通过健康检查后启动，启动脚本自动执行数据库迁移。

## 2. 目录结构

```
fund_pooling/
├── Dockerfile                 # 三阶段构建（前端 / 依赖 / 运行时），构建上下文为仓库根目录
├── docker/
│   ├── entrypoint.sh          # 等待 DB → migrate → 启动 Gunicorn
│   └── wait_for_db.py
├── backend/
│   ├── config/                # Django 配置：settings / urls / wsgi / asgi
│   ├── apps/core/             # 业务 app：健康检查、系统信息、SPA 兜底
│   ├── gunicorn.conf.py
│   ├── manage.py
│   ├── pyproject.toml         # Python 依赖（uv）
│   ├── uv.lock                # 依赖锁定
│   └── .python-version        # 3.13
├── frontend/
│   ├── src/
│   │   ├── api/               # 接口封装（fetch + CSRF + 统一错误处理）
│   │   ├── auth/              # 登录状态（session）
│   │   ├── components/        # StatusCard 等组件
│   │   ├── router/            # 路由与登录守卫
│   │   ├── views/             # 页面：登录页 / 首页看板
│   │   ├── App.vue            # 布局（顶栏、用户信息、退出登录）
│   │   ├── main.ts
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts         # 开发代理 /api /admin /static → Django
├── docker-compose.yml         # db + web 编排（开发 / 单机共用）
├── docker-compose.prod.yml    # 生产覆盖：仅监听 127.0.0.1、不暴露 5432、资源限额
├── deploy/
│   ├── DEPLOY.md              # 单机部署指南（步骤 / 排错 / 安全清单）
│   ├── deploy.sh              # 一键部署：备份 → 构建/拉取 → 启动 → 健康检查
│   ├── Caddyfile              # Caddy 反代模板（自动 HTTPS）
│   └── nginx.conf             # Nginx 反代模板（配合 certbot）
├── database/                  # 本地 PostgreSQL 数据（gitignore，绝不提交）
├── .env                       # 本机实际配置（gitignore，已生成）
├── .env.example               # 配置模板
├── .dockerignore
├── Makefile                   # 常用命令
└── README.md
```

## 3. 快速开始

前置条件：

- Docker Desktop 已安装并启动（本机文件共享需包含 `/Users`，默认即包含）
- 本地开发可选：uv（Python 3.13）、Node.js ≥ 22

```bash
cd ~/Code/fund_pooling

# 环境变量：本仓库已生成 .env（含随机密钥、本地数据目录、备份目录）
# 新克隆时执行：
cp .env.example .env        # 然后修改 SECRET_KEY / POSTGRES_PASSWORD / PGDATA_HOST_PATH / BACKUP_HOST_PATH

# 构建并启动 db + web
make up

# 查看状态 / 日志
make ps
make logs
```

访问地址：

| 地址 | 说明 |
| --- | --- |
| http://localhost:8000 | 前端看板（Vue SPA，需登录） |
| http://localhost:8000/login | 登录页（未登录访问其他页面会自动跳转到这里） |
| http://localhost:8000/api/health/ | 健康检查（含数据库连通性） |
| http://localhost:8000/api/system/ | 运行环境信息 |
| http://localhost:8000/admin/ | Django 管理后台 |

**登录与鉴权**：前端使用 Django Session 认证，支持**用户名或邮箱**登录
（邮箱不区分大小写；同一邮箱对应多个账号时会被拒绝，请改用用户名）。
未登录访问 `/` 等页面时，路由守卫会跳转 `/login?redirect=<原地址>`，
登录成功后回到原地址；已登录访问 `/login` 会自动回首页。

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/auth/csrf/` | GET | 下发 CSRF Cookie（SPA 自动调用） |
| `/api/auth/me/` | GET | 当前登录用户，未登录返回 401 |
| `/api/auth/login/` | POST | 登录（`username` 字段接受用户名或邮箱，+ `password`） |
| `/api/auth/logout/` | POST | 退出登录 |

创建账号（登录页使用的就是 Django 用户）：

```bash
make superuser
# 或：在 .env 里配置 DJANGO_SUPERUSER_USERNAME / PASSWORD / EMAIL 后重新 make up
```

停止（**不会**删除本地数据库与备份文件）：

```bash
make down
```

## 4. 数据存储与备份

### 4.1 运行数据：本地 `./database`

数据库文件放在**本地磁盘**，路径由 `.env` 的 `PGDATA_HOST_PATH` 决定：

```
PGDATA_HOST_PATH="/Users/Licht/Code/fund_pooling/database"
```

挂载关系：

```
宿主机 PGDATA_HOST_PATH  ──bind mount──▶  容器 /var/lib/postgresql/data
                                          └── PGDATA=/var/lib/postgresql/data/pgdata
                                          └── 实际文件 = PGDATA_HOST_PATH/pgdata
```

确认挂载生效：

```bash
ls -lh database/pgdata | head
docker compose exec db psql -U fund_pooling -d fund_pooling -c '\l'
```

### 4.2 备份：写入宿主机备份目录

`pg_dump` 输出由 `.env` 的 `BACKUP_HOST_PATH` 指定（宿主机路径，**不挂载进容器**）：

```
BACKUP_HOST_PATH="/path/to/backups/fund_pooling"          # 可指向本地磁盘、NAS 或云同步目录
```

- 格式：`pg_dump -Fc`（自定义格式，压缩 + 可按需选择恢复）
- 保留策略：`BACKUP_KEEP_DAYS`（默认 14 天），`make backup` 会删除更早的 dump
- 手动备份：`make backup`；查看：`make backup-list`；恢复：`make restore FILE=fund_pooling-xxx.dump`
- 需要时重复执行 `make backup` 即可；过期 dump 会按 `BACKUP_KEEP_DAYS` 自动清理

> 备份文件由宿主机直接写入（`pg_dump` 标准输出重定向），归属当前用户，可直接读取或拷走；
> 写入时先落 `.part` 再改名，失败不会留下半截 dump。容器只挂载数据卷，
> 因此更换备份目录（包括换到 NAS / 对象存储）只需要改 `.env`，不用重建容器。

### 4.3 迁移数据目录 / 清空数据库

更换数据目录：

```bash
make down
# 修改 .env 的 PGDATA_HOST_PATH，把旧 pgdata/ 整个拷贝到新目录
make up
```

> 若此前数据曾放在云同步目录（早期配置），迁移后旧目录会以 `pgdata.migrated-*` 的形式保留，
> 确认本地运行无误后可自行删除。

彻底清空数据库（**危险**）：

```bash
make down
rm -rf database/pgdata
make up
```

## 5. 本地开发（热更新，不重建镜像）

`.env` 中 `DJANGO_DEBUG=true` 只对本地 `runserver` 生效；docker compose 会强制覆盖为 `false`。
Django 配置会自动加载仓库根目录的 `.env`。

```bash
make dev-db        # 1. 只启动数据库容器（127.0.0.1:5432）
make dev-backend   # 2. 本地 Django，自动重载 → http://localhost:8000
make dev-frontend  # 3. Vite 热更新 → http://localhost:5173
```

Vite 会把 `/api`、`/admin`、`/static` 代理到 `http://127.0.0.1:8000`，前端无需处理跨域。

后端依赖管理（uv）：

```bash
cd backend
uv sync                 # 安装依赖（含 dev）
uv add <package>        # 新增依赖并更新 uv.lock
uv run python manage.py <command>
uv run ruff check .
```

新建业务 app：

```bash
cd backend
uv run python manage.py startapp fund apps/fund
# 把 "apps.fund" 加入 config/settings.py 的 INSTALLED_APPS，然后 makemigrations
```

前端依赖管理：

```bash
cd frontend
npm install
npm add <package>
npm run build      # 产出 dist/
```

## 6. 常用命令

| 命令 | 说明 |
| --- | --- |
| `make up` | 构建并启动 db + web |
| `make down` | 停止并移除容器（保留本地数据与备份文件） |
| `make deploy` | 生产部署 / 更新（调用 `deploy/deploy.sh`，可传 `ARGS="--skip-backup"`） |
| `make build` | 只构建 web 镜像 |
| `make ps` / `make logs` | 查看状态 / 跟踪日志 |
| `make migrate` | 容器内执行数据库迁移 |
| `make makemigrations` | 生成迁移文件 |
| `make shell` | 容器内 Django shell |
| `make superuser` | 创建后台管理员 |
| `make test` | 后端测试（容器内） |
| `make lint` / `make format` | ruff + 前端类型检查 / 格式化 |
| `make backup` | `pg_dump` 到备份目录（自动清理过期备份） |
| `make backup-list` | 列出备份文件 |
| `make restore FILE=fund_pooling-xxx.dump` | 从备份恢复 |
| `make info` | 查看本地数据目录与备份目录占用 |
| `make dev-db` / `dev-backend` / `dev-frontend` | 本地开发三件套 |

## 7. 环境变量

见 [.env.example](.env.example)，关键项：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | — | 生产必须更换，随机长字符串 |
| `DJANGO_DEBUG` | `true` | 本地开发用；compose 内固定为 `false` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | 生产填域名，逗号分隔 |
| `CSRF_TRUSTED_ORIGINS` | — | HTTPS 域名，如 `https://example.com` |
| `POSTGRES_DB/USER/PASSWORD` | `fund_pooling` | 容器初始化时创建 |
| `POSTGRES_PORT_HOST` | `5432` | 映射到宿主机（仅 127.0.0.1） |
| `PGDATA_HOST_PATH` | — | 数据库数据目录（本地磁盘绝对路径） |
| `BACKUP_HOST_PATH` | — | `pg_dump` 备份输出目录（宿主机路径，仅 `make backup/restore` 使用） |
| `BACKUP_KEEP_DAYS` | `14` | 备份保留天数 |
| `WEB_PORT` | `8000` | 前端/接口对外端口 |
| `APP_VERSION` | `0.1.0` | 同时作为 web 镜像 tag |
| `GUNICORN_WORKERS` / `GUNICORN_THREADS` | CPU×2+1 / 2 | Gunicorn 调优 |

密钥生成：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 8. 镜像构建与镜像管理

`web` 镜像为三阶段构建（根目录 `Dockerfile`）——该镜像同时包含前端产物与后端服务，
所以 Dockerfile 放在仓库根目录，构建上下文也是根目录：

1. `node:22-alpine`：`npm ci` + `vite build`，构建时 `VITE_BASE=/static/`；
2. `python:3.13-slim-bookworm` + uv 官方镜像：`uv sync --frozen --no-dev`，依赖层可缓存；
3. `python:3.13-slim-bookworm`：拷贝虚拟环境与代码、把前端产物放进 `staticfiles/`、
   `collectstatic` 补齐 admin 静态文件，以非 root 用户 `app` 运行 Gunicorn。

常用镜像操作：

```bash
docker compose build                 # 构建 web 镜像并打 tag fund_pooling/web:0.1.0
docker compose images                # 查看镜像
docker compose push web              # 推送到镜像仓库（需 docker login）
docker compose pull                  # 拉取镜像
docker compose up -d --build         # 构建 + 启动
docker compose up -d --force-recreate web   # 仅重建 web
```

## 9. 生产部署

完整步骤、排错与安全清单见 **[deploy/DEPLOY.md](deploy/DEPLOY.md)**，这里是速览：

1. 服务器准备 Docker（Compose ≥ 2.24），`database/` 目录 chown 999:999；
2. 配置 `.env`：`DJANGO_SECRET_KEY`、`POSTGRES_PASSWORD`、`DJANGO_ALLOWED_HOSTS=<域名>`、
   `CSRF_TRUSTED_ORIGINS=https://<域名>`，`PGDATA_HOST_PATH` / `BACKUP_HOST_PATH` 指向服务器本地目录；
3. 部署：`make deploy` 或 `./deploy/deploy.sh`（首次加 `--skip-backup`），
   自动备份 → 构建/拉取 → 启动 → 健康检查；
4. 宿主机前置 Caddy / Nginx 处理 HTTPS，转发到 `127.0.0.1:8000`
   （模板见 `deploy/Caddyfile`、`deploy/nginx.conf`）；
5. 生产编排用 `docker-compose.prod.yml` 叠加：只监听 127.0.0.1、不暴露 5432、资源限额、Gunicorn 3 worker。

```bash
# 部署 / 更新
make deploy
./deploy/deploy.sh              # 等价写法，参数更直观
# 生产环境手动操作
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

## 10. 测试与检查

```bash
make test                      # Django 测试（容器内，需 db 运行）
cd backend && uv run ruff check . && uv run ruff format --check .
cd frontend && npm run type-check
```

## 11. 常见问题

- **端口占用**：修改 `.env` 的 `WEB_PORT` / `POSTGRES_PORT_HOST`。
- **web 反复重启**：`make logs web` 查看，多为数据库未就绪或密码不一致；
  entrypoint 会等待数据库并在失败时退出。
- **前端 503「前端尚未构建」**：说明直接跑了 Django 而没构建镜像，
  用 `make up`，开发时访问 Vite（5173）。
- **备份文件在哪**：`make info` / `make backup-list` 会直接打印 `BACKUP_HOST_PATH`
  的实际取值；保留天数由 `BACKUP_KEEP_DAYS` 控制。
- **路径含空格**：`BACKUP_HOST_PATH` 路径含空格时必须在 `.env` 中加引号。
- **Docker Desktop 文件共享**：需包含 `/Users`（默认包含），否则本地 `database/` 无法挂载。
- **构建报 `failed to update builder last activity time ... operation not permitted`**：
  BuildKit 无法写入 `~/.docker/buildx/activity`。把 buildx 配置目录指到可写位置即可：
  `BUILDX_CONFIG=$(mktemp -d) docker compose build`。不要用 `DOCKER_BUILDKIT=0` 绕过——
  Dockerfile 使用了 `RUN --mount`，旧构建器不支持。
- **首次启动较慢**：`db` 健康检查 `start_period` 60s，`web` 需等 `db` healthy。
- **局域网 / 其他设备访问**：把访问地址的 IP 或域名加入 `.env` 的
  `DJANGO_ALLOWED_HOSTS`（如 `localhost,127.0.0.1,192.168.1.10`）。
- **`auth_*` / `django_*` 表为什么和业务表同库？**：这是 Django 的标准形态，
  **不建议拆成独立的 user/auth 库**——跨库外键不被支持（业务模型
  `ForeignKey(AUTH_USER_MODEL)` 会失效）、`transaction.atomic()` 无法跨库，
  且 Admin / Session / ContentType 都依赖 `auth_user` 在同一库；
  而这些表体积很小（约 440 KB，全库 8.6 MB）。要扩展用户字段时，加
  `UserProfile`（OneToOne）或自定义 `AUTH_USER_MODEL`；要多系统统一登录时，
  拆的是**认证服务**（OIDC / Keycloak），而不是数据库。
- **忘记密码 / 新增登录账号**：`docker compose exec web python manage.py changepassword <用户名>`；
  新增账号 `make superuser`（或在 Admin 的用户管理里创建）。
- **可以用邮箱登录吗**：可以，登录页输入用户名或邮箱都行（邮箱不区分大小写）。
  邮箱需在 Admin 用户资料或 `create_user(..., email=...)` 中填写；若同一邮箱对应多个账号，
  登录会被拒绝，请改用用户名。
- **如何进入数据库**：`docker compose exec db psql -U fund_pooling -d fund_pooling`。

## License

MIT
