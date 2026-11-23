"""核心接口：健康检查、系统信息、SPA 入口。"""

import platform
import time

import django
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class ApiRootView(APIView):
    """API 索引，方便快速确认服务是否正常。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "service": "fund-pooling-backend",
                "version": settings.APP_VERSION,
                "endpoints": {
                    "health": request.build_absolute_uri("health/"),
                    "system": request.build_absolute_uri("system/"),
                    "admin": request.build_absolute_uri("/admin/"),
                },
            }
        )


class HealthView(APIView):
    """健康检查：同时探测数据库连通性，供容器 HEALTHCHECK 使用。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        started = time.perf_counter()
        database_ok = True
        error: str | None = None

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:  # pragma: no cover - 仅在数据库异常时触发
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

    def get(self, request):
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

    def get(self, request, *args, **kwargs):
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
