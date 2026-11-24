"""核心应用的 AppConfig。"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """核心应用的配置。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "核心"
