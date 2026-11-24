"""核心应用的测试：健康检查、系统信息、SPA 入口。"""

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import RequestFactory, TestCase, override_settings

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
