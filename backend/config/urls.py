"""Django 路由入口。

- `/admin/`     Django 管理后台
- `/api/`       核心接口（健康检查、系统信息）
- `/api/auth/`  账号与第三方登录接口
- 其余路径      返回 Vue SPA 的入口（容器内前端产物已构建进 staticfiles）

各 app 的 URLconf 在这里平级挂载，避免出现 ``core:accounts:`` 这类嵌套命名空间。
"""

from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import SpaView

admin.site.site_header = "Fund Pooling 管理后台"
admin.site.site_title = "Fund Pooling"
admin.site.index_title = "系统管理"

# Django 约定：app_name / urlpatterns 必须小写
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.core.urls")),
    # SPA 兜底：API / 后台 / 静态资源之外的路径都交给前端路由
    re_path(r"^(?!api/|admin/|static/|media/).*$", SpaView.as_view(), name="spa"),
]
