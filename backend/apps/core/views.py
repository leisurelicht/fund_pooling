"""核心接口：健康检查、系统信息、登录鉴权、SPA 入口。"""

import platform
import time

import django
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.db import connection
from django.db.utils import DatabaseError
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.csrf import csrf_failure as default_csrf_failure
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
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


def serialize_user(user) -> dict:
    """返回给前端的用户信息（不含敏感字段）。"""
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


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
                    "me": request.build_absolute_uri("auth/me/"),
                    "login": request.build_absolute_uri("auth/login/"),
                    "logout": request.build_absolute_uri("auth/logout/"),
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


class CsrfView(APIView):
    """下发 CSRF Cookie（Vite 开发服务器直接提供页面时需要先补一次）。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """确保客户端拿到 csrftoken Cookie 并返回 token 值。"""
        return Response({"csrfToken": get_token(request)})


class MeView(APIView):
    """当前登录用户；未登录返回 401，供前端路由守卫判断。"""

    permission_classes = [AllowAny]

    def get(self, request):
        """已登录返回用户信息，未登录返回 401。"""
        if not request.user.is_authenticated:
            return Response({"detail": "未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"user": serialize_user(request.user)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """用户名 / 邮箱 + 密码登录，成功后写入 Django session。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """校验用户名/邮箱和密码，成功则创建登录会话。"""
        # `username` 字段兼容用户名或邮箱（也接受 identifier 别名）
        identifier = str(
            request.data.get("username") or request.data.get("identifier") or ""
        ).strip()
        password = str(request.data.get("password", ""))

        if not identifier or not password:
            return Response(
                {"detail": "请输入用户名/邮箱和密码"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=identifier, password=password)
        if user is None:
            return Response(
                {"detail": "用户名/邮箱或密码错误"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_active:
            return Response(
                {"detail": "账号已被禁用"},
                status=status.HTTP_403_FORBIDDEN,
            )

        django_login(request, user)
        return Response({"user": serialize_user(user)})


class LogoutView(APIView):
    """退出登录，清除会话。"""

    def post(self, request):
        """结束当前会话，返回 204。"""
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
