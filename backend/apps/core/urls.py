from django.urls import path

from apps.core.views import ApiRootView, HealthView, SystemInfoView

app_name = "core"

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("health/", HealthView.as_view(), name="health"),
    path("system/", SystemInfoView.as_view(), name="system"),
]
