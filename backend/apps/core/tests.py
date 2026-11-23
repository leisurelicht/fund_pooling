from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from apps.core.views import SpaView


class HealthApiTests(TestCase):
    def test_health_returns_ok_with_database(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["database"]["status"], "ok")

    def test_api_root_lists_endpoints(self):
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("health", response.json()["endpoints"])

    def test_system_info(self):
        response = self.client.get("/api/system/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database_engine"], "django.db.backends.postgresql")

    def test_unknown_api_path_is_404(self):
        response = self.client.get("/api/not-exists/")
        self.assertEqual(response.status_code, 404)


class SpaViewTests(TestCase):
    def test_returns_index_html_when_built(self):
        with TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.html"
            index.write_text("<html><body>spa</body></html>", encoding="utf-8")
            with override_settings(STATIC_ROOT=Path(tmp)):
                response = SpaView().get(None, None)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"spa", response.content)

    def test_returns_503_when_index_missing(self):
        with TemporaryDirectory() as tmp, override_settings(STATIC_ROOT=Path(tmp)):
            response = SpaView().get(None, None)

        self.assertEqual(response.status_code, 503)
