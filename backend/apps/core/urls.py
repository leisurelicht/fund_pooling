"""核心应用的 API 路由（挂载在 ``/api/`` 下）。

账号相关的路由由 ``config/urls.py`` 直接挂到 ``/api/auth/``，见
``apps.accounts.urls``。SPA 兜底也在 ``config/urls.py``，不要放在这里——
那样会把未知的 ``/api/*`` 也变成 200。
"""

from django.urls import path

from apps.core.views import ApiRootView, HealthView, SystemInfoView

# Django 约定：app_name / urlpatterns 必须小写
app_name = "core"

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("health/", HealthView.as_view(), name="health"),
    path("system/", SystemInfoView.as_view(), name="system"),
]
