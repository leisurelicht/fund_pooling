"""账号域的后台管理。

- 收紧 ``auth.User`` 的邮箱校验（模型层 email 可选，但数据库层有非空约束）
- 注册第三方账号绑定表
- 预留用户档案（Profile）
"""

from django import forms
from django.contrib import admin
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User

from apps.accounts.models import Profile, SocialAccount

_EMAIL_HELP = "必填：数据库层有 auth_user_email_required 非空约束"


class EmailRequiredUserCreationForm(UserCreationForm):
    """``auth.User.email`` 在模型层是可选的，这里补上必填校验。"""

    email = forms.EmailField(required=True, help_text=_EMAIL_HELP)

    class Meta(UserCreationForm.Meta):
        """在默认的新增字段基础上带上 email。"""

        model = User
        fields = ("username", "email")


class EmailRequiredUserChangeForm(UserChangeForm):
    """编辑用户时同样不允许把邮箱清空。"""

    email = forms.EmailField(required=True, help_text=_EMAIL_HELP)

    class Meta(UserChangeForm.Meta):
        """沿用默认字段集合。"""

        model = User
        fields = "__all__"


class SocialAccountInline(admin.TabularInline):
    """在用户详情页直接查看该用户的第三方绑定。"""

    model = SocialAccount
    extra = 0
    fields = ("provider", "provider_uid", "created_at")
    readonly_fields = ("provider", "provider_uid", "created_at")

    def has_add_permission(self, request, obj=None):
        """绑定由登录流程创建，内联里只能看和删。"""
        return False


class ProfileInline(admin.StackedInline):
    """在用户详情页直接编辑档案，未创建时可直接补充。"""

    model = Profile
    extra = 0
    fields = ("display_name", "avatar_url", "locale")
    verbose_name_plural = "用户档案"


# auth.admin 已经把 User 注册了，先注销再换成收紧校验的版本
try:
    admin.site.unregister(User)
except NotRegistered:  # pragma: no cover — 仅在 auth 未注册时触发
    pass


@admin.register(User)
class EmailRequiredUserAdmin(UserAdmin):
    """沿用默认 UserAdmin，只把两个表单换成「邮箱必填」版本。"""

    form = EmailRequiredUserChangeForm
    add_form = EmailRequiredUserCreationForm
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )
    inlines = (SocialAccountInline, ProfileInline)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    """第三方账号绑定关系。

    只提供「查看 / 删除」：绑定记录由登录流程创建，手工新增容易造出
    指向错误用户的数据，因此不开放新增入口。
    """

    list_display = ("id", "provider", "provider_uid", "user", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("provider_uid", "user__username", "user__email")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50

    def has_add_permission(self, request):
        """绑定只能由登录流程创建，后台不提供新增。"""
        return False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """用户档案（预留：显示名、头像、界面语言）。"""

    list_display = ("id", "user", "display_name", "locale", "updated_at")
    search_fields = ("user__username", "user__email", "display_name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)
    list_per_page = 50
