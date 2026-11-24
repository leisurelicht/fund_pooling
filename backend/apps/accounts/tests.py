"""账号应用的测试：登录鉴权、第三方登录、邮箱约束、后台注册。"""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.auth_apple import AppleUserInfo
from apps.accounts.auth_google import GoogleUserInfo
from apps.accounts.models import SocialAccount


class AuthConfigApiTests(TestCase):
    """前端运行时配置接口。"""

    @override_settings(GOOGLE_CLIENT_ID="gid.apps.googleusercontent.com", APPLE_CLIENT_ID="")
    def test_auth_config_exposes_client_ids(self):
        """前端运行时配置应下发已配置的 client id，未配置的为空串。"""
        response = self.client.get(reverse("accounts:auth-config"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["google_client_id"], "gid.apps.googleusercontent.com")
        self.assertEqual(response.json()["apple_client_id"], "")


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
            reverse("accounts:auth-login"),
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
        response = self.client.get(reverse("accounts:auth-me"))
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
            reverse("accounts:auth-login"),
            data=json.dumps({"username": self.username, "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "CSRF 校验失败，请刷新页面后重试")

    def test_login_then_me_then_logout(self):
        """完整会话流程：登录 → 查询当前用户 → 登出 → 未登录。"""
        self.assertEqual(self.login().status_code, 200)

        me = self.client.get(reverse("accounts:auth-me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["username"], self.username)

        self.assertEqual(self.client.post(reverse("accounts:auth-logout")).status_code, 204)

        self.assertEqual(self.client.get(reverse("accounts:auth-me")).status_code, 401)


class SocialLoginApiTests(TestCase):
    """第三方登录：首次注册、重复登录、邮箱自动关联与异常分支。"""

    def google_login(self, *, sub="google-sub-1", email="g@example.com", verified=True):
        """mock 掉 token 校验，只测试绑定 / 建号逻辑。"""
        info = GoogleUserInfo(
            sub=sub,
            email=email,
            email_verified=verified,
            name="G User",
            given_name="G",
            family_name="User",
        )
        with patch("apps.accounts.views.verify_google_id_token", return_value=info):
            return self.client.post(
                reverse("accounts:auth-google"),
                data=json.dumps({"credential": "fake-id-token"}),
                content_type="application/json",
            )

    def apple_login(self, *, sub="apple-sub-1", email="a@example.com", verified=True):
        """mock 掉 Apple token 校验，验证共用流程接线正确。"""
        info = AppleUserInfo(sub=sub, email=email, email_verified=verified)
        with patch("apps.accounts.views.verify_apple_id_token", return_value=info):
            return self.client.post(
                reverse("accounts:auth-apple"),
                data=json.dumps(
                    {
                        "id_token": "fake-id-token",
                        "full_name": {"given_name": "三", "family_name": "张"},
                    }
                ),
                content_type="application/json",
            )

    def test_google_first_login_creates_user_and_binding(self):
        """首次登录应创建用户 + 绑定，并用会话保持登录态。"""
        response = self.google_login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "g@example.com")

        user = User.objects.get(email="g@example.com")
        self.assertEqual(user.username, "UserG")
        self.assertEqual(user.social_accounts.get(provider="google").provider_uid, "google-sub-1")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.client.get(reverse("accounts:auth-me")).status_code, 200)

    def test_google_second_login_reuses_bound_user(self):
        """同一 sub 再次登录应复用已绑定账号，不重复建号。"""
        first = self.google_login()
        second = self.google_login(email="g-changed@example.com")

        self.assertEqual(first.json()["user"]["id"], second.json()["user"]["id"])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 1)

    def test_email_match_binds_existing_user(self):
        """邮箱已被核验且能唯一匹配时，应关联到已有账号而非新建。"""
        existing = User.objects.create_user(
            "tester", email="tester@example.com", password="pw-123456"
        )

        response = self.google_login(sub="google-sub-9", email="Tester@Example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], existing.pk)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            existing.social_accounts.get(provider="google").provider_uid, "google-sub-9"
        )

    def test_unverified_email_does_not_auto_bind(self):
        """邮箱未经 provider 核验时不得自动关联，避免冒用邮箱接管账号。"""
        victim = User.objects.create_user(
            "victim", email="victim@example.com", password="pw-123456"
        )

        response = self.google_login(
            sub="google-sub-evil", email="victim@example.com", verified=False
        )

        # 不能关联、又不能重复占用该邮箱 → 明确拒绝，而不是悄悄建一个无邮箱账号
        self.assertEqual(response.status_code, 409)
        self.assertIn("已被其它账号使用", response.json()["detail"])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 0)
        victim.refresh_from_db()
        self.assertEqual(victim.email, "victim@example.com")

    def test_login_without_email_is_rejected(self):
        """provider 未返回邮箱时无法建号（email 必填）。"""
        response = self.google_login(sub="google-sub-noemail", email=None)

        self.assertEqual(response.status_code, 400)
        self.assertIn("邮箱", response.json()["detail"])
        self.assertEqual(User.objects.count(), 0)

    def test_ambiguous_email_is_rejected(self):
        """数据库已保证邮箱唯一，该分支作为约束被移除时的兜底提示。"""
        User.objects.create_user("dup1", email="dup@example.com", password="pw-123456")

        with patch.object(User.objects, "get", side_effect=User.MultipleObjectsReturned):
            response = self.google_login(sub="google-sub-dup", email="dup@example.com")

        self.assertEqual(response.status_code, 400)
        self.assertIn("已关联多个账号", response.json()["detail"])
        self.assertEqual(SocialAccount.objects.count(), 0)

    def test_disabled_account_is_rejected(self):
        """已禁用账号即使绑定正确也不能登录。"""
        user = User.objects.create_user("banned", email="banned@example.com", password="pw-123456")
        user.is_active = False
        user.save(update_fields=["is_active"])
        SocialAccount.objects.create(user=user, provider="google", provider_uid="google-sub-x")

        response = self.google_login(sub="google-sub-x", email="banned@example.com")

        self.assertEqual(response.status_code, 403)
        self.assertIn("账号已被禁用", response.json()["detail"])

    def test_missing_credential_is_rejected(self):
        """缺少 credential 应返回 400。"""
        response = self.client.post(
            reverse("accounts:auth-google"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_token_is_rejected(self):
        """token 校验失败应返回 400 且不建号。"""
        with patch(
            "apps.accounts.views.verify_google_id_token", side_effect=ValueError("签名无效")
        ):
            response = self.client.post(
                reverse("accounts:auth-google"),
                data=json.dumps({"credential": "bad-token"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("签名无效", response.json()["detail"])
        self.assertEqual(User.objects.count(), 0)

    def test_apple_login_uses_full_name_from_client(self):
        """Apple 的名称只来自前端 full_name，应写入用户名与绑定信息。"""
        response = self.apple_login()

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="a@example.com")
        self.assertEqual(user.username, "张三")
        self.assertEqual(
            user.social_accounts.get(provider="apple").extra_data["name"],
            {"given_name": "三", "family_name": "张"},
        )


class UserEmailUniquenessTests(TestCase):
    """auth_user.email 的「必填 + 大小写不敏感唯一」约束（迁移 0002 / 0003）。"""

    def test_duplicate_email_is_rejected(self):
        """同一邮箱（忽略大小写）不允许建第二个账号。"""
        User.objects.create_user("first", email="alice@example.com", password="pw-123456")

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("second", email="Alice@Example.com", password="pw-123456")

        self.assertEqual(User.objects.count(), 1)

    def test_email_is_required(self):
        """空邮箱会被 CHECK 约束拒绝。"""
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("noemail", email="", password="pw-123456")

        self.assertEqual(User.objects.count(), 0)

    def test_blank_email_is_rejected(self):
        """纯空白邮箱同样不允许。"""
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("spaces", email="   ", password="pw-123456")

        self.assertEqual(User.objects.count(), 0)


class AdminTests(TestCase):
    """后台可访问性：第三方绑定表已注册、用户表单已收紧为邮箱必填。"""

    def setUp(self):
        """建超级用户并登录后台。"""
        self.superuser = User.objects.create_superuser(
            "root", email="root@example.com", password="pw-123456"
        )
        self.client.force_login(self.superuser)

    def test_admin_index_lists_social_account(self):
        """后台首页应能进入 SocialAccount 列表（说明已注册）。"""
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("admin:accounts_socialaccount_changelist"))

    def test_social_account_changelist(self):
        """绑定列表页可打开并展示记录。"""
        SocialAccount.objects.create(user=self.superuser, provider="google", provider_uid="g-1")
        response = self.client.get(reverse("admin:accounts_socialaccount_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "g-1")

    def test_user_add_form_requires_email(self):
        """后台新增用户时邮箱为必填。"""
        response = self.client.get(reverse("admin:auth_user_add"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["adminform"].form.fields["email"].required)

    def test_user_change_form_requires_email(self):
        """后台编辑用户时邮箱同样必填。"""
        response = self.client.get(reverse("admin:auth_user_change", args=[self.superuser.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["adminform"].form.fields["email"].required)
