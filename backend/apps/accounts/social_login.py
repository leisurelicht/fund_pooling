"""社交账号登录的共用流程。

Apple / Google 等 provider 只负责验证 id_token 并给出 `(uid, email, name)`，
剩下的「查绑定 → 邮箱匹配 → 建用户 → 建绑定 → 写会话」集中在这里，
避免每个 provider 各复制一份。
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.db import IntegrityError, transaction

from apps.accounts.models import SocialAccount

logger = logging.getLogger(__name__)

User = get_user_model()

# Django 默认 User.username 的 max_length 是 150，留出 `_N` 后缀的余量
_USERNAME_MAX_LENGTH = 140


class SocialLoginError(Exception):
    """可直接返回给前端的业务错误（自带建议的 HTTP 状态码）。"""

    def __init__(self, detail: str, status_code: int = 400):
        """保存错误详情与状态码。"""
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _find_bound_user(provider: str, uid: str):
    """按 provider + uid 查已绑定的本地用户，不存在返回 None。"""
    social = (
        SocialAccount.objects.filter(provider=provider, provider_uid=uid)
        .select_related("user")
        .first()
    )
    return social.user if social is not None else None


def _create_user(*, provider: str, uid: str, email: str, full_name: dict):
    """按 provider 返回的资料创建本地用户（无可用密码，只能走第三方登录）。

    ``email`` 必填：数据库层有 ``auth_user_email_required`` 约束。
    """
    given_name = str(full_name.get("given_name", "")).strip()
    family_name = str(full_name.get("family_name", "")).strip()
    display_name = f"{family_name}{given_name}" if given_name else ""

    base_username = (
        display_name or email.split("@", maxsplit=1)[0].strip() or f"{provider}_{uid[:8]}"
    )[:_USERNAME_MAX_LENGTH]

    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        suffix = f"_{counter}"
        username = f"{base_username[: _USERNAME_MAX_LENGTH - len(suffix)]}{suffix}"
        counter += 1

    # create_user 不传 password 会生成 unusable password
    return User.objects.create_user(username=username, email=email)


def _bind(provider: str, uid: str, user, extra_data: dict) -> None:
    """在独立事务中写入绑定记录，唯一约束冲突时回滚该事务。"""
    with transaction.atomic():
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_uid=uid,
            extra_data=extra_data,
        )


def _create_user_and_binding(*, provider: str, uid: str, email: str, extra_data: dict):
    """在同一事务内创建用户与绑定，任一约束冲突则整体回滚（不留孤儿账号）。"""
    with transaction.atomic():
        user = _create_user(provider=provider, uid=uid, email=email, full_name=extra_data["name"])
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_uid=uid,
            extra_data=extra_data,
        )
    return user


def _match_by_email(provider_label: str, email: str | None, email_verified: bool):
    """仅在邮箱已被 provider 核验时按邮箱匹配已有账号。

    未核验的邮箱若也用于自动关联，等于允许冒用他人邮箱接管账号，因此直接跳过。
    """
    if not (email and email_verified):
        return None
    try:
        return User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        raise SocialLoginError(
            f"该邮箱已关联多个账号，请先使用用户名/邮箱登录，然后在设置中绑定{provider_label}。"
        ) from None


def _fill_missing_email(provider: str, user, email: str | None) -> None:
    """已绑定用户的邮箱为空时补写；该邮箱已被别的账号占用则跳过。"""
    if not email or user.email:
        return
    user.email = email
    try:
        with transaction.atomic():
            user.save(update_fields=["email"])
    except IntegrityError:
        logger.info("%s 登录补写邮箱 %s 与其它账号冲突，已跳过", provider, email)
        user.refresh_from_db(fields=["email"])


def _attach_binding(provider: str, uid: str, user, extra_data: dict):
    """给已有账号补建绑定；并发绑定冲突时回退到已绑定账号。"""
    try:
        _bind(provider, uid, user, extra_data)
    except IntegrityError:
        logger.info("%s 并发绑定，回退到已绑定账号 uid=%s", provider, uid)
        return _find_bound_user(provider, uid) or user
    return user


def _create_account(
    provider: str, uid: str, email: str | None, extra_data: dict, provider_label: str
):
    """新建账号并绑定，处理三种失败：无邮箱、并发抢先、邮箱被占用。"""
    if not email:
        # email 必填（数据库约束），provider 没给就没法建号
        raise SocialLoginError(
            f"未能从{provider_label}获取到邮箱，无法创建账号。"
            f"请在{provider_label}授权时允许共享邮箱后重试。",
            400,
        )

    try:
        return _create_user_and_binding(
            provider=provider, uid=uid, email=email, extra_data=extra_data
        )
    except IntegrityError:
        # 并发请求已抢先完成绑定 → 刚才创建的用户已随事务回滚
        user = _find_bound_user(provider, uid)
        if user is not None:
            return user
        logger.info("%s 建号冲突且无并发绑定，判定为邮箱占用 uid=%s email=%s", provider, uid, email)
        raise SocialLoginError(
            f"该邮箱已被其它账号使用，请先用用户名/邮箱登录，然后在设置中绑定{provider_label}。",
            409,
        ) from None


# PLR0913：参数均为关键字参数、每个 provider 只有一个调用点，拆成对象反而增加噪音
def login_with_social_account(  # noqa: PLR0913
    request,
    *,
    provider: str,
    uid: str,
    provider_label: str,
    email: str | None = None,
    email_verified: bool = False,
    full_name: dict | None = None,
):
    """按第三方账号登录 / 注册 / 关联本地账号，并写入 Django session。

    Args:
        provider: provider 标识，如 ``apple`` / ``google``
        uid: provider 返回的稳定用户标识（``sub``）
        provider_label: 面向用户的 provider 名称，用于错误提示
        email: provider 返回的邮箱；空邮箱无法建号
        email_verified: provider 是否已核验该邮箱；未核验时不做自动关联
        full_name: ``{"given_name": ..., "family_name": ...}``

    Returns:
        已登录的本地 User

    Raises:
        SocialLoginError: 账号被禁用、邮箱歧义等可预期的业务错误
    """
    # provider 一般不会返回带空白的邮箱，但唯一索引区分空白，先归一化再说
    email = (email or "").strip() or None
    extra_data = {"email": email, "name": full_name or {}}

    user = _find_bound_user(provider, uid)
    if user is not None:
        if not user.is_active:
            raise SocialLoginError("账号已被禁用", 403)
        _fill_missing_email(provider, user, email)
    else:
        user = _match_by_email(provider_label, email, email_verified)
        if user is not None and not user.is_active:
            raise SocialLoginError("账号已被禁用", 403)
        user = (
            _create_account(provider, uid, email, extra_data, provider_label)
            if user is None
            else _attach_binding(provider, uid, user, extra_data)
        )

    django_login(request, user)
    return user
