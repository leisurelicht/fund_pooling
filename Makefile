SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE ?= docker compose
BACKEND := backend
FRONTEND := frontend

# 从 .env 读取变量值（去掉包裹的双引号）
envval = $$(sed -n 's/^$(1)=//p' .env | sed 's/"//g')

.PHONY: help env build up down restart logs ps migrate makemigrations shell superuser \
	test lint format dev dev-db dev-backend dev-frontend info backup backup-list restore deploy

help: ## 显示所有可用命令
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

env: ## 根据 .env.example 生成 .env（已存在则跳过）
	@test -f .env || { cp .env.example .env; echo "已生成 .env，请修改 DJANGO_SECRET_KEY / POSTGRES_PASSWORD / PGDATA_HOST_PATH / BACKUP_HOST_PATH"; }
	@test -f .env && echo "使用现有 .env"

build: env ## 构建 web 镜像
	$(COMPOSE) build

up: env ## 构建并启动 db + web 两个容器
	$(COMPOSE) up -d --build
	@echo "前端: http://localhost:$${WEB_PORT:-8000}  |  后台: http://localhost:$${WEB_PORT:-8000}/admin/"

down: ## 停止并移除容器（本地数据与 iCloud 备份都不受影响）
	$(COMPOSE) down

deploy: ## 生产部署 / 更新（备份 → 构建或拉取 → 启动 → 健康检查）
	@./deploy/deploy.sh $(ARGS)

restart: ## 重启所有容器
	$(COMPOSE) restart

logs: ## 跟踪查看容器日志
	$(COMPOSE) logs -f --tail=100

ps: ## 查看容器状态
	$(COMPOSE) ps

migrate: ## 在 web 容器内执行数据库迁移
	$(COMPOSE) exec web python manage.py migrate

makemigrations: ## 生成数据库迁移文件
	$(COMPOSE) exec web python manage.py makemigrations

shell: ## 进入 Django shell
	$(COMPOSE) exec web python manage.py shell

superuser: ## 创建 Django 后台管理员
	$(COMPOSE) exec web python manage.py createsuperuser

test: ## 运行后端测试（Django test runner）
	$(COMPOSE) exec web python manage.py test

lint: ## 后端 ruff + 前端类型检查
	cd $(BACKEND) && uv run ruff check .
	cd $(FRONTEND) && npm run type-check

format: ## 格式化后端代码
	cd $(BACKEND) && uv run ruff format .

dev: ## 本地开发（需开两个终端，参考 README）
	@echo "终端 1: make dev-backend   # Django http://localhost:8000"
	@echo "终端 2: make dev-frontend  # Vite   http://localhost:5173"
	@echo "先启动数据库: make dev-db"

dev-db: ## 只启动数据库容器（供本地开发使用）
	$(COMPOSE) up -d db

dev-backend: ## 本地运行 Django（自动重载）
	cd $(BACKEND) && uv run python manage.py runserver 0.0.0.0:8000

dev-frontend: ## 本地运行 Vite 开发服务器
	cd $(FRONTEND) && npm run dev

info: ## 查看数据目录（本地）与备份目录（iCloud）占用
	@DATA="$(call envval,PGDATA_HOST_PATH)"; BK="$(call envval,BACKUP_HOST_PATH)"; \
	echo "数据目录（本地）: $$DATA"; du -sh "$$DATA" 2>/dev/null || echo "  （尚未初始化）"; \
	echo; echo "备份目录（iCloud）: $$BK"; du -sh "$$BK" 2>/dev/null || echo "  （尚无备份）"; \
	ls -lht "$$BK" 2>/dev/null | head -6

backup: ## 导出数据库到 iCloud 备份目录（pg_dump 输出重定向落盘，容器无需挂载）
	@set -euo pipefail; \
	BK="$(call envval,BACKUP_HOST_PATH)"; \
	mkdir -p "$$BK"; \
	OUT="$$BK/fund_pooling-$$(date +%Y%m%d-%H%M%S).dump"; \
	$(COMPOSE) exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -Fc' > "$$OUT.part"; \
	mv "$$OUT.part" "$$OUT"; \
	echo "备份完成：$$OUT"; \
	KEEP="$(call envval,BACKUP_KEEP_DAYS)"; \
	find "$$BK" -maxdepth 1 -name 'fund_pooling-*.dump' -mtime +$${KEEP:-14} -delete

backup-list: ## 列出 iCloud 中的备份文件
	@BK="$(call envval,BACKUP_HOST_PATH)"; \
	if [ -d "$$BK" ]; then ls -lht "$$BK" | head -20; else echo "（尚无备份）"; fi

restore: ## 从 iCloud 备份恢复（FILE=fund_pooling-xxx.dump，先用 make backup-list 查看）
	@set -euo pipefail; \
	BK="$(call envval,BACKUP_HOST_PATH)"; \
	test -n "$(FILE)" || { echo "用法: make restore FILE=fund_pooling-20260101-030000.dump"; exit 1; }; \
	test -f "$$BK/$(FILE)" || { echo "备份不存在: $$BK/$(FILE)"; exit 1; }; \
	$(COMPOSE) exec -T db sh -c 'pg_restore -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" --clean --if-exists' < "$$BK/$(FILE)"; \
	echo "恢复完成：$(FILE)"
