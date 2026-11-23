# 部署指南（单机 Docker Compose）

本项目的交付形态是 **两个镜像 / 两个容器**（`postgres` + `web`），
`web` 镜像同时包含 Vue 前端构建产物与 Django 后端，所以部署一台机器 + 一个反向代理即可。

```
                    ┌──────────── 宿主机（Linux VPS / 本机）──────────────┐
 Internet ──443──▶  │ Caddy / Nginx（HTTPS、域名）                        │
                    │        │ 转发 127.0.0.1:8000                       │
                    │        ▼                                            │
                    │ web 容器（Gunicorn：/ 静态前端 + /api + /admin）     │
                    │        │ compose 内网                                │
                    │        ▼                                            │
                    │ db 容器（PostgreSQL，数据在本地 ./database）         │
                    └─────────────────────────────────────────────────────┘
```

相关文件：

| 文件 | 用途 |
| --- | --- |
| `docker-compose.yml` | 基础编排（本地开发 / 单机部署共用） |
| `docker-compose.prod.yml` | 生产覆盖：只监听 127.0.0.1、不暴露数据库端口、资源限额 |
| `deploy/deploy.sh` | 一键部署脚本（备份 → 构建/拉取 → 启动 → 健康检查） |
| `deploy/Caddyfile` | Caddy 反代模板（自动 HTTPS） |
| `deploy/nginx.conf` | Nginx 反代模板（配合 certbot） |

## 1. 前置条件

- Linux 服务器（1 核 2G 起，推荐 2 核 4G），或长期开机的 Mac
- Docker Engine + Compose 插件（**≥ v2.24**，生产覆盖文件用到 `!reset` / `!override`）

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"     # 重新登录生效
docker compose version              # 确认 >= v2.24
```

## 2. 获取代码与目录

```bash
sudo mkdir -p /srv/fund_pooling && sudo chown "$USER" /srv/fund_pooling
git clone git@github.com:leisurelicht/fund_pooling.git /srv/fund_pooling
cd /srv/fund_pooling

mkdir -p database backup

# 关键：Linux 上 bind mount 使用真实权限，postgres 容器以 uid 999 运行
sudo chown -R 999:999 database
```

> macOS 上的 Docker Desktop 会自动映射权限，Linux 不会；漏掉 chown 会导致
> `initdb: could not change permissions of directory` 或容器反复重启。

## 3. 配置 `.env`

```bash
cp .env.example .env
chmod 600 .env
vi .env
```

服务器上**必须修改**的项：

| 变量 | 说明 |
| --- | --- |
| `DJANGO_SECRET_KEY` | 重新生成：`python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `POSTGRES_PASSWORD` | 强密码 |
| `DJANGO_ALLOWED_HOSTS` | 你的域名，如 `fund.example.com`（漏了会 400） |
| `CSRF_TRUSTED_ORIGINS` | `https://fund.example.com` |
| `PGDATA_HOST_PATH` | `/srv/fund_pooling/database`（不要用 iCloud 路径） |
| `BACKUP_HOST_PATH` | `/srv/fund_pooling/backup` |
| `WEB_PORT` | 默认 `8000`（仅本机监听，供反代） |

可选：

| 变量 | 说明 |
| --- | --- |
| `APP_VERSION` | 镜像 tag，发布时递增便于回滚 |
| `WEB_IMAGE` | 使用镜像仓库时填写，如 `ghcr.io/you/fund_pooling/web` |
| `GUNICORN_WORKERS` | 默认生产 3，小机器可设 2 |
| `DJANGO_SUPERUSER_*` | 首次启动自动创建后台管理员 |

`DJANGO_DEBUG` 无需修改，`docker-compose.yml` 中已固定为 `false`。

## 4. 部署

### 首次部署

```bash
./deploy/deploy.sh --skip-backup
# 或
make deploy ARGS="--skip-backup"
```

脚本会：构建镜像 → `up -d --wait` → 请求 `/api/health/` 验证。
首次启动 entrypoint 会自动执行数据库迁移。

### 日常发布

```bash
git pull
make deploy                   # 自动备份 → 构建 → 更新 → 健康检查
# 等价的直接调用：./deploy/deploy.sh
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--build` | 强制在服务器构建镜像 |
| `--pull` | 强制从镜像仓库拉取 |
| `--git` | 先执行 `git pull --ff-only` |
| `--skip-backup` | 跳过部署前备份 |
| `--dry-run` | 只打印将执行的命令 |

### 镜像仓库模式（推荐用于正式环境）

CI 负责构建推送，服务器只拉取：

```bash
# CI
APP_VERSION=1.2.0 WEB_IMAGE=ghcr.io/you/fund_pooling/web docker compose build
docker compose push web

# 服务器
# .env 中设置：APP_VERSION=1.2.0
#              WEB_IMAGE=ghcr.io/you/fund_pooling/web
./deploy/deploy.sh --pull
```

## 5. 反向代理与 HTTPS

### Caddy（自动证书，最简单）

```bash
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/fund.example.com/你的域名/' /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

### Nginx + certbot

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/fund_pooling.conf
sudo sed -i 's/fund.example.com/你的域名/' /etc/nginx/conf.d/fund_pooling.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d 你的域名
```

反代需传递 `Host` 与 `X-Forwarded-Proto`，后端已配置
`SECURE_PROXY_SSL_HEADER`，HTTPS 判定与 CSRF 校验才能正确工作。

## 6. 验证清单

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl -fsS http://127.0.0.1:8000/api/health/          # {"status":"ok", "database":{"status":"ok"...}}
curl -fsS https://你的域名/api/health/
```

- 浏览器访问 `https://你的域名/` 应看到前端看板
- `https://你的域名/admin/` 能打开登录页（先 `docker compose exec web python manage.py createsuperuser`）
- `docker compose ... logs web` 无 traceback
- 端口检查：`ss -tlnp | grep -E '8000|5432'` 只应出现 127.0.0.1:8000

## 7. 升级与回滚

```bash
# 升级（脚本自动先备份）
git pull
./deploy/deploy.sh

# 回滚代码/镜像（数据库迁移不可逆，回滚前确认兼容或用备份恢复）
# 1) 切回旧版本代码
git checkout <旧 commit>
# 2) 切回旧镜像 tag（需镜像仍在本地/仓库）
APP_VERSION=1.1.0 ./deploy/deploy.sh --pull --skip-backup
```

## 8. 备份与恢复

部署前脚本会自动备份到 `BACKUP_HOST_PATH`。手动操作：

```bash
make backup                  # 需要 make；或使用 deploy.sh --skip-backup 之外的方式
make restore FILE=fund_pooling-20260101-030000.dump
```

可选：定时备份（cron，按需启用，注意 `%` 需转义）：

```cron
15 3 * * * cd /srv/fund_pooling && docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "/srv/fund_pooling/backup/fund_pooling-$(date +\%Y\%m\%d).dump"
```

生产环境建议再同步一份到异地（对象存储 / 另一台机器），避免磁盘故障时备份同时丢失。

## 9. 排错

| 现象 | 原因 / 处理 |
| --- | --- |
| db 反复重启，日志 `could not change permissions` | `database/` 未 chown 999:999（见第 2 节） |
| 访问域名返回 400 Bad Request | `.env` 的 `DJANGO_ALLOWED_HOSTS` 没加域名 |
| 502 Bad Gateway | web 容器未起或端口不对：`docker compose ... ps`、`logs web` |
| 登录后台提示 CSRF 失败 | `CSRF_TRUSTED_ORIGINS` 没配 `https://域名` |
| 健康检查一直失败 | 首次启动较慢；看 `logs db`，确认数据库已 healthy |
| `!reset` 解析报错 | Compose 版本 < 2.24，升级 Docker Compose |
| SELinux 机器启动失败 | bind mount 加 `:z`：`"${PGDATA_HOST_PATH}:/var/lib/postgresql/data:z"` |
| 构建时 OOM | 服务器内存不足，加 swap 或改用镜像仓库模式 |

## 10. 安全清单（上线前逐项确认）

- [ ] `DJANGO_SECRET_KEY`、`POSTGRES_PASSWORD` 已换成随机强值（不是 `change-me`）
- [ ] `.env` 权限 600，且不在 git 里
- [ ] `DJANGO_ALLOWED_HOSTS`、`CSRF_TRUSTED_ORIGINS` 只包含正式域名
- [ ] 8000 / 5432 没有暴露到公网（只监听 127.0.0.1）
- [ ] 反向代理已启用 HTTPS，并设置 HSTS（模板已包含）
- [ ] 防火墙只开放 22 / 80 / 443
- [ ] 已配置异地备份与恢复演练
- [ ] 定期 `docker compose ... pull` 更新基础镜像（postgres / python / node 补丁）
