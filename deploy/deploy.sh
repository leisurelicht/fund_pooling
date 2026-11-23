#!/usr/bin/env bash
# =============================================================================
# fund_pooling 单机部署脚本
#
#   ./deploy/deploy.sh                # 自动判断：有 WEB_IMAGE 就打 pull，否则本地 build
#   ./deploy/deploy.sh --build        # 强制在服务器构建镜像
#   ./deploy/deploy.sh --pull         # 强制从镜像仓库拉取
#   ./deploy/deploy.sh --git          # 先执行 git pull --ff-only
#   ./deploy/deploy.sh --skip-backup  # 跳过部署前自动备份（首次部署也需要）
#   ./deploy/deploy.sh --dry-run      # 只打印将执行的命令，不做任何修改
#
# 使用前请确认 .env 已按服务器环境配置（参考 deploy/DEPLOY.md）。
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE=".env"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

MODE="auto"
DO_GIT=0
DO_BACKUP=1
DRY_RUN=0

usage() { sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; }

for arg in "$@"; do
  case "$arg" in
    --build) MODE="build" ;;
    --pull) MODE="pull" ;;
    --git) DO_GIT=1 ;;
    --skip-backup) DO_BACKUP=0 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数：$arg（--help 查看用法）" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
die() { echo "错误：$1" >&2; exit 1; }

# dry-run 时只打印命令
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    echo
  else
    "$@"
  fi
}

envval() { sed -n "s/^$1=//p" "$ENV_FILE" 2>/dev/null | sed 's/"//g' || true; }

# ---------------------------------------------------------------------------
# 前置检查
# ---------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || die "缺少 .env，请先 cp .env.example .env 并填写（参考 deploy/DEPLOY.md）"
[ -f docker-compose.prod.yml ] || die "缺少 docker-compose.prod.yml"

WEB_PORT="$(envval WEB_PORT)"
WEB_PORT="${WEB_PORT:-8000}"
WEB_IMAGE="$(envval WEB_IMAGE)"

if [ "$MODE" = "auto" ]; then
  if [ -n "$WEB_IMAGE" ]; then
    MODE="pull"
  else
    MODE="build"
  fi
fi

if grep -vE '^[[:space:]]*#' "$ENV_FILE" | grep -q 'change-me'; then
  echo "警告：.env 中仍有 change-me 占位值，请确认 DJANGO_SECRET_KEY / POSTGRES_PASSWORD 已更换" >&2
fi

if [ "$DO_GIT" -eq 1 ]; then
  log "拉取代码"
  run git pull --ff-only
fi

if [ "$DRY_RUN" -eq 0 ]; then
  command -v docker >/dev/null 2>&1 || die "未安装 Docker"
  docker info >/dev/null 2>&1 || die "Docker 未运行（systemctl start docker）"
fi

# 首次部署时数据库还没起来，自动跳过备份
if [ "$DO_BACKUP" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
  if [ -z "$("${COMPOSE[@]}" ps -q db 2>/dev/null || true)" ]; then
    echo "未检测到运行中的 db 容器，跳过备份（首次部署）"
    DO_BACKUP=0
  fi
fi

# ---------------------------------------------------------------------------
# 1. 部署前备份
# ---------------------------------------------------------------------------
if [ "$DO_BACKUP" -eq 1 ]; then
  BK="$(envval BACKUP_HOST_PATH)"
  [ -n "$BK" ] || die ".env 缺少 BACKUP_HOST_PATH"
  NAME="fund_pooling-predeploy-$(date +%Y%m%d-%H%M%S).dump"

  log "部署前备份 → $BK/$NAME"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] pg_dump → $BK/$NAME"
  else
    mkdir -p "$BK"
    "${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BK/$NAME.part"
    mv "$BK/$NAME.part" "$BK/$NAME"
  fi
fi

# ---------------------------------------------------------------------------
# 2. 获取镜像
# ---------------------------------------------------------------------------
if [ "$MODE" = "build" ]; then
  log "在服务器构建镜像"
  run "${COMPOSE[@]}" build
else
  log "从镜像仓库拉取镜像"
  run "${COMPOSE[@]}" pull
fi

# ---------------------------------------------------------------------------
# 3. 启动 / 更新（entrypoint 会自动执行数据库迁移）
# ---------------------------------------------------------------------------
log "启动 / 更新容器"
run "${COMPOSE[@]}" up -d --wait --wait-timeout 180

# ---------------------------------------------------------------------------
# 4. 健康检查
# ---------------------------------------------------------------------------
log "健康检查 http://127.0.0.1:${WEB_PORT}/api/health/"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "[dry-run] 跳过健康检查"
else
  for i in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${WEB_PORT}/api/health/" >/dev/null 2>&1; then
      echo "健康检查通过"
      break
    fi
    if [ "$i" -eq 30 ]; then
      "${COMPOSE[@]}" ps || true
      die "健康检查失败，请查看日志：${COMPOSE[*]} logs web"
    fi
    sleep 2
  done
fi

run "${COMPOSE[@]}" ps

echo
echo "部署完成：服务仅监听 127.0.0.1:${WEB_PORT}，请通过反向代理（HTTPS）访问。"
echo "反向代理配置参考：deploy/Caddyfile 或 deploy/nginx.conf"
