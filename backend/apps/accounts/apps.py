"""账号相关应用的 AppConfig。"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """账号与第三方登录绑定。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "账号"
