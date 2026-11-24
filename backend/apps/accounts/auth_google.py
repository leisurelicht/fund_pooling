"""Google Sign In 的 id_token 验证逻辑。"""

import logging
from dataclasses import dataclass

import jwt
from django.conf import settings
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

GOOGLE_KEYS_URL = "https://www.googleapis.com/oauth2/v3/certs"
# Google 的 iss 声明有两种写法，官方要求两种都接受
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")

# PyJWKClient 内部缓存 Google 公钥（kid 匹配 + 过期自动刷新）。
# 模块级实例：Gunicorn 多 worker 下每个 worker 独立维护缓存。
_jwks_client = PyJWKClient(GOOGLE_KEYS_URL, cache_keys=True)


@dataclass
class GoogleUserInfo:
    """Google id_token 解码后的用户信息。"""

    sub: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None


def _as_bool(value) -> bool:
    """Google 的 email_verified 可能是 bool 也可能是字符串 'true'。"""
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def verify_google_id_token(id_token: str) -> GoogleUserInfo:
    """验证 Google id_token 并返回用户信息。

    PyJWKClient 自动完成：拉取 Google 公钥（已缓存）、按 kid 匹配公钥、验证 RS256 签名。

    Raises:
        ValueError: token 无效、签名不匹配，或服务端未配置 GOOGLE_CLIENT_ID
    """
    audience = settings.GOOGLE_CLIENT_ID
    if not audience:
        raise ValueError("服务端未配置 GOOGLE_CLIENT_ID，无法校验 Google 登录")

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(id_token)
    except jwt.PyJWTError as exc:
        raise ValueError(f"无法获取 Google 签名密钥: {exc}") from exc

    try:
        payload = jwt.decode(
            id_token,
            key=signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            options={"verify_exp": True},
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"Google id_token 验证失败: {exc}") from exc

    # PyJWT 的 issuer 参数只接受单值，而 Google 有两种写法，这里自行校验
    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise ValueError("Google id_token 签发方不合法")

    return GoogleUserInfo(
        sub=payload["sub"],
        email=payload.get("email"),
        email_verified=_as_bool(payload.get("email_verified")),
        name=payload.get("name"),
        given_name=payload.get("given_name"),
        family_name=payload.get("family_name"),
    )
