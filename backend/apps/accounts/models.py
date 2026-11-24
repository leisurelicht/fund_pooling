"""账号域模型：第三方登录绑定与用户档案。

``auth.User`` 是 Django 内置模型，这里只通过外键/一对一挂接补充信息，
不替换 ``AUTH_USER_MODEL``。
"""

from django.conf import settings
from django.db import models


class SocialAccount(models.Model):
    """外部社交账号关联表。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=32)  # 'apple'、'google' 等
    provider_uid = models.CharField(max_length=512)  # Apple sub / Google sub
    extra_data = models.JSONField(default=dict)  # 用户名、邮箱等附加信息
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """同一 provider 下的 uid 只能绑定一次。"""

        verbose_name = "第三方账号绑定"
        verbose_name_plural = "第三方账号绑定"
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "provider_uid"),
                name="unique_social_account",
            )
        ]

    def __str__(self) -> str:
        """便于在 Admin 与日志中辨识。"""
        return f"{self.provider}:{self.provider_uid} → {self.user}"


class Profile(models.Model):
    """用户档案：与 ``auth_user`` 一对一，存放不宜塞进 ``auth_user`` 的资料。

    预留用途：显示名、头像、界面语言等。记录按需创建
    （``Profile.objects.get_or_create(user=...)``），不在建号时自动插行。
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=64, blank=True)
    avatar_url = models.URLField(max_length=512, blank=True)
    locale = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """一人一份档案。"""

        verbose_name = "用户档案"
        verbose_name_plural = "用户档案"

    def __str__(self) -> str:
        """优先显示自定义名称，否则回退到用户名。"""
        return self.display_name or self.user.get_username()
