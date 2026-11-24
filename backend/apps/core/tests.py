"""核心应用测试：健康检查、登录鉴权、SPA 入口。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.core.views import SpaView


class HealthApiTests(TestCase):
    """健康检查与系统信息接口。"""

    def test_health_returns_ok_with_database(self):
        """健康检查应返回 200 且数据库状态正常。"""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["database"]["status"], "ok")

    def test_api_root_lists_endpoints(self):
        """API 根路径应列出已注册的接口。"""
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)
        endpoints = response.json()["endpoints"]
        self.assertIn("health", endpoints)
        self.assertIn("login", endpoints)

    def test_system_info(self):
        """系统信息应返回运行环境与数据库引擎。"""
        response = self.client.get("/api/system/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database_engine"], "django.db.backends.postgresql")

    def test_unknown_api_path_is_404(self):
        """未定义的 API 路径应返回 404（不能落到 SPA）。"""
        response = self.client.get("/api/not-exists/")
        self.assertEqual(response.status_code, 404)


class AuthApiTests(TestCase):
    """登录 / 登出 / 当前用户接口。"""

    def setUp(self):
        """创建测试用户（带邮箱，便于验证邮箱登录）。"""
        self.username = "tester"
        self.email = "Tester@Example.com"
        self.password = "test-pass-123"
        User.objects.create_user(self.username, email=self.email, password=self.password)

    def login(self, username=None, password=None):
        """以 JSON 方式调用登录接口，便于各用例复用。"""
        return self.client.post(
            reverse("core:auth-login"),
            data=json.dumps(
                {
                    "username": self.username if username is None else username,
                    "password": self.password if password is None else password,
                }
            ),
            content_type="application/json",
        )

    def test_me_requires_login(self):
        """未登录访问当前用户接口应返回 401。"""
        response = self.client.get(reverse("core:auth-me"))
        self.assertEqual(response.status_code, 401)

    def test_login_success_returns_user(self):
        """用户名 + 正确密码应登录成功并返回用户信息。"""
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["username"], self.username)

    def test_login_with_email(self):
        """使用邮箱也应可以登录。"""
        response = self.login(username=self.email)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["username"], self.username)

    def test_login_with_email_is_case_insensitive(self):
        """邮箱登录不区分大小写。"""
        response = self.login(username=self.email.lower())
        self.assertEqual(response.status_code, 200)

    def test_login_with_ambiguous_email_is_rejected(self):
        """同一邮箱对应多个账号时应拒绝登录。"""
        User.objects.create_user("tester2", email=self.email.lower(), password=self.password)
        response = self.login(username=self.email)
        self.assertEqual(response.status_code, 400)
        self.assertIn("用户名/邮箱或密码错误", response.json()["detail"])

    def test_login_wrong_password(self):
        """密码错误应返回 400。"""
        response = self.login(password="wrong-password")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_login_missing_fields(self):
        """缺少用户名或密码应返回 400。"""
        response = self.login(username="", password="")
        self.assertEqual(response.status_code, 400)

    def test_login_requires_csrf(self):
        """登录接口必须校验 CSRF，失败时返回 JSON 提示。"""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse("core:auth-login"),
            data=json.dumps({"username": self.username, "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "CSRF 校验失败，请刷新页面后重试")

    def test_login_then_me_then_logout(self):
        """完整会话流程：登录 → 查询当前用户 → 登出 → 未登录。"""
        self.assertEqual(self.login().status_code, 200)

        me = self.client.get(reverse("core:auth-me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["username"], self.username)

        self.assertEqual(self.client.post(reverse("core:auth-logout")).status_code, 204)

        self.assertEqual(self.client.get(reverse("core:auth-me")).status_code, 401)


class SpaViewTests(TestCase):
    """SPA 入口（index.html）与 CSRF Cookie 下发。"""

    def test_returns_index_html_when_built(self):
        """前端已构建时应返回 index.html。"""
        with TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.html"
            index.write_text("<html><body>spa</body></html>", encoding="utf-8")
            with override_settings(STATIC_ROOT=Path(tmp)):
                response = SpaView().get(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"spa", response.content)

    def test_returns_503_when_index_missing(self):
        """前端未构建时应返回 503 并提示。"""
        with TemporaryDirectory() as tmp, override_settings(STATIC_ROOT=Path(tmp)):
            response = SpaView().get(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 503)

    def test_sets_csrf_cookie(self):
        """SPA 入口应下发 csrftoken Cookie（登录 POST 需要）。"""
        response = self.client.get("/")
        self.assertIn("csrftoken", response.cookies)
