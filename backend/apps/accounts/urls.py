"""账号相关接口的路由。

挂载在 ``/api/auth/`` 下（见 ``apps/core/urls.py``），因此这里的路径都不再带
``auth/`` 前缀。
"""

from django.urls import path

from apps.accounts.views import (
    AppleLoginView,
    AuthConfigView,
    CsrfView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
)

# Django 约定：app_name / urlpatterns 必须小写
app_name = "accounts"

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("config/", AuthConfigView.as_view(), name="auth-config"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("apple/", AppleLoginView.as_view(), name="auth-apple"),
    path("google/", GoogleLoginView.as_view(), name="auth-google"),
]
