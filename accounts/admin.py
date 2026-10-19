from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts import services
from accounts.models import GroupAssignment, GuardianProfile, MentorProfile, User
from common.roles import Role


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "last_login",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    add_fieldsets = (
        (None, {"fields": ("email", "password1", "password2", "role", "first_name", "last_name")}),
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name")}),
        ("Role", {"fields": ("role",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Keep role profiles consistent even for users created via the admin.
        if obj.role in (Role.MENTOR, Role.GUARDIAN):
            services._ensure_profile(obj, obj.role)


@admin.register(GuardianProfile)
class GuardianProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "deleted_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone")
    list_filter = ("deleted_at",)


class GroupAssignmentInline(admin.TabularInline):
    model = GroupAssignment
    extra = 0


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_id", "deleted_at")
    search_fields = ("user__email", "employee_id")
    list_filter = ("deleted_at",)
    inlines = [GroupAssignmentInline]
    filter_horizontal = ("specializations",)


@admin.register(GroupAssignment)
class GroupAssignmentAdmin(admin.ModelAdmin):
    list_display = ("mentor", "group", "assigned_by", "created_at")
    search_fields = ("mentor__user__email", "group__name")
