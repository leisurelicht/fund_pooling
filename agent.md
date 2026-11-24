# fund_pooling — Agent 指南

Django 6.1 + DRF + Vue 3 + Vite 8 + TypeScript + PostgreSQL 17 全栈项目。
uv 管理 Python 依赖，Docker Compose 编排 `postgres:17-alpine` + 自建 web 镜像。

## 架构

- **同容器同端口**：前端产物打进 `staticfiles/`，Django 以 `/static/` 提供，Gunicorn 统一服务
- **路由**：`/api/*` → DRF    `/admin/*` → Django Admin    其余 → Vue SPA 兜底
- **鉴权**：Django Session + `EmailOrUsernameBackend`（用户名或邮箱登录，邮箱大小写不敏感）
- **CSRF**：登录页自动下发 csrftoken，`client.ts` 统一封装自动带 `X-CSRFToken`
- **Docker 构建**：三阶段 — node 构建前端 → uv sync 装 Python 依赖 → slim 运行时

## 目录约定

```
fund_pooling/
├── backend/
│   ├── config/          # settings / urls / wsgi / asgi
│   ├── apps/core/       # 核心 app（健康检查、系统信息、SPA 入口；无模型、无迁移）
│   ├── apps/accounts/   # 账号域（登录会话、第三方绑定、邮箱约束、用户档案）
│   └── pyproject.toml   # uv 依赖 + ruff 规则
├── frontend/src/
│   ├── api/             # fetch 封装、CSRF、错误处理
│   ├── auth/            # 登录状态管理
│   ├── router/          # vue-router + 登录守卫
│   └── views/           # 页面组件
├── docker/              # entrypoint.sh、wait_for_db.py
├── database/pgdata/     # PG 数据（gitignore，绝不提交）
└── deploy/              # 部署脚本与配置
```

## 编码约定

### Python（Django）

- ruff 规则：`E, F, I, N, D1, UP, B, DJ, PL` — docstring 必备，命名 snake_case。
  `PL` 是 Pylint 规则集的 Ruff 移植，本项目用它替代 Pylint（不要再装 Pylint 扩展）
- 类型检查：`uv run mypy .` 必须零报错（django-stubs 插件已配置，ORM 的 `objects` 等
  动态成员无需手写类型）；新增第三方库要自带类型存根，否则会报缺存根
- Django 特例：`app_name`、`urlpatterns` 保持小写（加注释说明，不要加 `noqa`）
- 未使用参数：前缀 `_request`；但**覆写父类方法时必须沿用父类的参数名与类型注解**，
  否则 mypy 会报 `override` 错误
- 异常：数据库层用 `DatabaseError`，不裸 `except Exception`
- 测试：类按功能分组，`setUp` 创建共享数据
- 自定义认证后端：用 `self.user_can_authenticate(user)` 检查 `is_active`

### TypeScript（Vue）

- `<script setup lang="ts">`，组合式 API
- 状态管理：`auth/session.ts` 为 reactive 单例，无需 Pinia
- 路由：`public: true` meta 放行未登录页；登录守卫在 `beforeEach` 中调 `loadSession()`
- API：`client.ts` 统一封装，POST 自动带 `X-CSRFToken`，`credentials: 'same-origin'`

### Docker

- 两个容器：`postgres:17-alpine` + 自建 web 镜像（三阶段构建）
- `entrypoint.sh` 等数据库就绪后自动 migrate
- **改 `.env` 后用 `make reload`（重建容器、不重建镜像）；`make restart` 只重启进程，不会重读 `.env`**
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml` 叠加生产覆盖

## 文档规范

### 设计文档（`docs/*.md`）

**只写核心思路、设计与实施流程，不写代码。** 源码是实现的唯一事实来源，文档写「为什么这样设计」
和「流程怎么走」。

具体规则：

- **不出现代码块**：不贴 Python / TypeScript / SQL / shell / 配置样例
- **不出现实现级参数**：像素值、字段长度、阈值、组件名、函数名等细节一律不写
- **路径只写到模块级**：说「accounts 的登录流程」，而不是逐文件列路径清单
- **每处设计必须给出「为什么」**：只写结论的文档无法判断日后能否改动
- **用表格与编号列表承载结构**：职责划分、接口清单、失败分支、决策对照、配置项
- **必须覆盖的章节**：目标、架构与职责划分、设计决策及理由、流程步骤、边界与失败情况、
  外部依赖与配置、测试覆盖、迁移策略、未来扩展、修订记录
- **如实记录缺口**：错误提示或文案里提到但尚未实现的入口，必须写进「未来扩展」，
  不能让文档许诺不存在的能力

### 修订记录

设计文档末尾维护版本表，每次实质修改追加一行，写明「改了什么」与「为什么改」。
不要直接覆盖历史结论——保留演进过程，便于回溯当初的取舍。

## 日常任务

- **新增接口**：对应 app 的 `views.py` 加 `APIView` 子类 → `urls.py` 加路由 → 需鉴权设
  `permission_classes = [IsAuthenticated]`（全局默认 AllowAny）。账号相关放 `apps/accounts`，
  其余放 `apps/core`
- **新增页面**：`views/` 下新建组件 → `router/index.ts` 加路由（需登录则不加 `meta: { public: true }`）
- **新增模型**：按域选 app 的 `models.py` 定义 → `makemigrations` → `migrate` → 序列化器 + 视图 + 路由