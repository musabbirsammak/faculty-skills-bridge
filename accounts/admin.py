from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, Faculty, Institution, User


@admin.register(User)
class TeacherAdmin(UserAdmin):
    list_display = ("username", "display_name", "department", "role", "is_active", "date_joined")
    list_filter = ("is_active", "role", "department__faculty", "department")
    search_fields = ("username", "display_name", "email")
    fieldsets = UserAdmin.fieldsets + (
        ("Teacher", {"fields": ("display_name", "department", "designation", "field", "role")}),
    )
    actions = ["activate_accounts"]

    @admin.action(description="Activate selected accounts")
    def activate_accounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} account(s).")


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name")
    inlines = [DepartmentInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "faculty")
    list_filter = ("faculty",)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "email_domains", "require_approval")

    def has_add_permission(self, request):
        return not Institution.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
