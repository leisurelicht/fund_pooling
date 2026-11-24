"""Apple Sign In 的 id_token 验证逻辑。"""

import logging
from dataclasses import dataclass

import jwt
from django.conf import settings
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

# PyJWKClient 内部缓存 Apple 公钥（过期自动刷新）。
# 模块级实例：Gunicorn 多 worker 下每个 worker 独立维护缓存，
# 各自首次使用时拉取一次 Apple 公钥，对性能无实质影响。
_jwks_client = PyJWKClient(APPLE_KEYS_URL, cache_keys=True)


@dataclass
class AppleUserInfo:
    """Apple id_token 解码后的用户信息。"""

    sub: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None


def _as_bool(value) -> bool:
    """Apple 的 email_verified 是字符串 'true' / 'false'，需要显式转换。"""
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def verify_apple_id_token(id_token: str) -> AppleUserInfo:
    """验证 Apple id_token 并返回用户信息。

    PyJWKClient 自动完成：
      - 拉取 Apple 公钥（已缓存）
      - 从 JWT header 读取 kid 并匹配对应 public key
      - 验证 RS256 签名

    Raises:
        ValueError: token 无效或验证失败
    """
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(id_token)
    except jwt.PyJWTError as exc:
        raise ValueError(f"无法获取 Apple 签名密钥: {exc}") from exc

    audience = settings.APPLE_CLIENT_ID
    try:
        payload = jwt.decode(
            id_token,
            key=signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=APPLE_ISSUER,
            options={"verify_exp": True},
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"Apple id_token 验证失败: {exc}") from exc

    return AppleUserInfo(
        sub=payload["sub"],
        email=payload.get("email"),
        email_verified=_as_bool(payload.get("email_verified")),
        name=payload.get("name"),
    )
