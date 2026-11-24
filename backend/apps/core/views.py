"""核心接口：健康检查、系统信息、SPA 入口。

账号 / 登录相关接口见 ``apps.accounts.views``。
"""

import platform
import time

import django
from django.conf import settings
from django.db import connection
from django.db.utils import DatabaseError
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views import View
from django.views.csrf import csrf_failure as default_csrf_failure
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def csrf_failure(request, reason: str = ""):
    """API 请求的 CSRF 失败返回 JSON，其余（如 Admin）沿用 Django 默认页面。"""
    if request.path.startswith("/api/"):
        return JsonResponse(
            {"detail": "CSRF 校验失败，请刷新页面后重试"},
            status=403,
        )
    return default_csrf_failure(request, reason)


class ApiRootView(APIView):
    """API 索引，方便快速确认服务是否正常。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """返回服务版本与主要接口地址。"""
        return Response(
            {
                "service": "fund-pooling-backend",
                "version": settings.APP_VERSION,
                "endpoints": {
                    "health": request.build_absolute_uri("health/"),
                    "system": request.build_absolute_uri("system/"),
                    "csrf": request.build_absolute_uri("auth/csrf/"),
                    "config": request.build_absolute_uri("auth/config/"),
                    "me": request.build_absolute_uri("auth/me/"),
                    "login": request.build_absolute_uri("auth/login/"),
                    "logout": request.build_absolute_uri("auth/logout/"),
                    "apple": request.build_absolute_uri("auth/apple/"),
                    "google": request.build_absolute_uri("auth/google/"),
                    "admin": request.build_absolute_uri("/admin/"),
                },
            }
        )


class HealthView(APIView):
    """健康检查：同时探测数据库连通性，供容器 HEALTHCHECK 使用。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, _request):
        """探测数据库并返回服务健康状态。"""
        started = time.perf_counter()
        database_ok = True
        error: str | None = None

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError as exc:  # pragma: no cover — 仅在数据库异常时触发
            database_ok = False
            error = f"{type(exc).__name__}: {exc}"

        database_latency_ms = round((time.perf_counter() - started) * 1000, 2)
        payload = {
            "status": "ok" if database_ok else "error",
            "service": "fund-pooling-backend",
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
            "time": timezone.localtime().isoformat(),
            "database": {
                "status": "ok" if database_ok else "error",
                "latency_ms": database_latency_ms,
                "error": error,
            },
        }
        http_status = 200 if database_ok else 503
        return Response(payload, status=http_status)


class SystemInfoView(APIView):
    """运行环境信息，便于排查部署问题。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, _request):
        """返回 Python / Django / 数据库等运行环境信息。"""
        return Response(
            {
                "service": "fund-pooling-backend",
                "version": settings.APP_VERSION,
                "debug": settings.DEBUG,
                "python": platform.python_version(),
                "django": django.get_version(),
                "platform": platform.platform(),
                "timezone": settings.TIME_ZONE,
                "database_engine": settings.DATABASES["default"]["ENGINE"],
                "database_host": settings.DATABASES["default"]["HOST"],
                "database_name": settings.DATABASES["default"]["NAME"],
            }
        )


class SpaView(View):
    """未命中任何 API 的前端路由，统一返回 Vue SPA 的 index.html。"""

    def get(self, request):
        """返回前端入口，并确保客户端拿到 CSRF Cookie。"""
        # 让 SPA 拿到 CSRF token（登录 / 登出等 POST 请求需要 X-CSRFToken 头）
        get_token(request)

        index_file = settings.STATIC_ROOT / "index.html"
        try:
            content = index_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return JsonResponse(
                {
                    "detail": "前端尚未构建",
                    "hint": (
                        "开发环境请访问 Vite 开发服务器（默认 http://localhost:5173），"
                        "或构建 Docker 镜像后再访问本地址。"
                    ),
                },
                status=503,
            )

        response = HttpResponse(content, content_type="text/html; charset=utf-8")
        response["Cache-Control"] = "no-cache"
        return response
