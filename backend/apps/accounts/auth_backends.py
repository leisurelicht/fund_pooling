"""自定义认证后端：支持用户名或邮箱登录。"""

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.http import HttpRequest


class EmailOrUsernameBackend(ModelBackend):
    """用户名精确匹配；否则按邮箱（不区分大小写）匹配。

    邮箱匹配到多个账号时拒绝登录，提示用户改用用户名。
    """

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        """先按用户名精确匹配，再按邮箱（不区分大小写）匹配。"""
        user_model = get_user_model()
        identifier = username or kwargs.get(user_model.USERNAME_FIELD)

        if not identifier or password is None:
            return None

        # 1) 用户名精确匹配（保持 Django 默认的大小写敏感行为）
        try:
            user = user_model.objects.get_by_natural_key(identifier)
        except user_model.DoesNotExist:
            user = None

        if user is not None:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
            return None

        # 2) 邮箱匹配（不区分大小写）
        matches = list(user_model.objects.filter(email__iexact=identifier))
        if len(matches) == 1:
            user = matches[0]
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
