"""accounts 的初始迁移。

项目尚未部署、数据库可从零构建，所以把历史迁移合并成这一条：

1. ``accounts_socialaccount`` —— 第三方账号绑定
2. ``accounts_profile`` —— 用户档案（预留）
3. ``auth_user`` 的两条邮箱约束 —— 大小写不敏感唯一 + 非空

``auth_user`` 的约束放在这里而不是 core：core 已不再持有任何模型，
而「邮箱必填且唯一」本身就是账号域的规则。
"""

from django.conf import settings
from django.db import migrations, models

CREATE_EMAIL_CONSTRAINTS = """
CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_ci_unique
    ON auth_user (lower(email));
ALTER TABLE auth_user
    ADD CONSTRAINT auth_user_email_required
    CHECK (email IS NOT NULL AND btrim(email) <> '');
"""

DROP_EMAIL_CONSTRAINTS = """
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_email_required;
DROP INDEX IF EXISTS auth_user_email_ci_unique;
"""


class Migration(migrations.Migration):
    """建立账号域的表结构与邮箱约束。"""

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("provider", models.CharField(max_length=32)),
                ("provider_uid", models.CharField(max_length=512)),
                ("extra_data", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="social_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "第三方账号绑定",
                "verbose_name_plural": "第三方账号绑定",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("provider", "provider_uid"),
                        name="unique_social_account",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("display_name", models.CharField(blank=True, max_length=64)),
                ("avatar_url", models.URLField(blank=True, max_length=512)),
                ("locale", models.CharField(blank=True, max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "用户档案",
                "verbose_name_plural": "用户档案",
            },
        ),
        migrations.RunSQL(CREATE_EMAIL_CONSTRAINTS, DROP_EMAIL_CONSTRAINTS),
    ]
