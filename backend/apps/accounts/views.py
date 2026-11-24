"""账号相关接口：会话、第三方登录、前端运行时配置。"""

import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth_apple import verify_apple_id_token
from apps.accounts.auth_google import verify_google_id_token
from apps.accounts.social_login import SocialLoginError, login_with_social_account

logger = logging.getLogger(__name__)


def serialize_user(user) -> dict:
    """返回给前端的用户信息（不含敏感字段）。"""
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


class CsrfView(APIView):
    """下发 CSRF Cookie（Vite 开发服务器直接提供页面时需要先补一次）。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """确保客户端拿到 csrftoken Cookie 并返回 token 值。"""
        return Response({"csrfToken": get_token(request)})


class AuthConfigView(APIView):
    """前端运行时配置：只下发可公开的第三方登录 client id。

    这些 id 本身就会出现在浏览器里，放在后端下发的好处是：
    换 client id 只要重启后端，不必重新构建前端产物。
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, _request):
        """返回已启用的第三方登录 client id（未配置则为空字符串）。"""
        return Response(
            {
                "google_client_id": settings.GOOGLE_CLIENT_ID,
                "apple_client_id": settings.APPLE_CLIENT_ID,
            }
        )


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


class AppleLoginView(APIView):
    """Apple 账号登录 / 注册 / 关联。

    POST /api/auth/apple/
    Body: { "id_token": "xxx", "full_name": { "given_name": "", "family_name": "" } | null }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """验证 Apple id_token 并登录或创建账号。"""
        id_token = str(request.data.get("id_token", "")).strip()
        if not id_token:
            return Response(
                {"detail": "缺少 Apple id_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            apple_user = verify_apple_id_token(id_token)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # id_token payload 不含显示名：名称只来自 JS SDK 的首次授权，
        # 由前端通过 full_name 单独传入
        try:
            user = login_with_social_account(
                request,
                provider="apple",
                uid=apple_user.sub,
                provider_label="Apple ID",
                email=apple_user.email,
                email_verified=apple_user.email_verified,
                full_name=request.data.get("full_name") or {},
            )
        except SocialLoginError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        return Response({"user": serialize_user(user)})


class GoogleLoginView(APIView):
    """Google 账号登录 / 注册 / 关联。

    POST /api/auth/google/
    Body: { "credential": "<Google ID token>" }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """验证 Google ID token 并登录或创建账号。"""
        # Google Identity Services 回调里字段名是 credential，这里兼容 id_token
        credential = str(
            request.data.get("credential") or request.data.get("id_token") or ""
        ).strip()
        if not credential:
            return Response(
                {"detail": "缺少 Google credential"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            google_user = verify_google_id_token(credential)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Google 的 id_token 自带 given_name / family_name，前端无需额外传
        full_name = request.data.get("full_name") or {
            "given_name": google_user.given_name or "",
            "family_name": google_user.family_name or "",
        }

        try:
            user = login_with_social_account(
                request,
                provider="google",
                uid=google_user.sub,
                provider_label="Google 账号",
                email=google_user.email,
                email_verified=google_user.email_verified,
                full_name=full_name,
            )
        except SocialLoginError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        return Response({"user": serialize_user(user)})
