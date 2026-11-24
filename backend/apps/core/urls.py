"""核心应用的 API 路由。"""

from django.urls import path

from apps.core.views import (
    ApiRootView,
    CsrfView,
    HealthView,
    LoginView,
    LogoutView,
    MeView,
    SystemInfoView,
)

# Django 命名空间约定，必须小写
# pylint: disable=invalid-name
app_name = "core"

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("health/", HealthView.as_view(), name="health"),
    path("system/", SystemInfoView.as_view(), name="system"),
    # 登录 / 登出 / 当前用户
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
]
