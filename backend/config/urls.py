"""Django 路由入口。

- `/admin/`  Django 管理后台
- `/api/`    后端接口
- 其余路径   返回 Vue SPA 的入口（容器内前端产物已构建进 staticfiles）
"""

from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import SpaView

admin.site.site_header = "Fund Pooling 管理后台"
admin.site.site_title = "Fund Pooling"
admin.site.index_title = "系统管理"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    # SPA 兜底：API / 后台 / 静态资源之外的路径都交给前端路由
    re_path(r"^(?!api/|admin/|static/|media/).*$", SpaView.as_view(), name="spa"),
]
