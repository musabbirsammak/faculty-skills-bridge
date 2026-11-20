from django.contrib import admin

from .models import Course, CourseEdit, CourseSkill, CourseStatusChange, CourseVote, Feedback, Skill, TeacherSkill


class CourseSkillInline(admin.TabularInline):
    model = CourseSkill
    autocomplete_fields = ("skill",)
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "area", "status", "department", "emerging", "impact", "updated")
    list_filter = ("status", "emerging", "impact", "field", "department")
    search_fields = ("title", "description")
    inlines = [CourseSkillInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "family", "added_by", "created")
    list_filter = ("family",)
    search_fields = ("name", "aliases")
    filter_horizontal = ("related",)


@admin.register(TeacherSkill)
class TeacherSkillAdmin(admin.ModelAdmin):
    list_display = ("teacher", "skill", "level", "updated")
    list_filter = ("level",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("course", "response", "updated")
    list_filter = ("response",)


@admin.register(CourseStatusChange)
class CourseStatusChangeAdmin(admin.ModelAdmin):
    list_display = ("course", "old_status", "new_status", "department", "changed_by", "created")
    list_filter = ("new_status",)


@admin.register(CourseEdit)
class CourseEditAdmin(admin.ModelAdmin):
    list_display = ("course", "proposed_by", "state", "decided_by", "created")
    list_filter = ("state",)


@admin.register(CourseVote)
class CourseVoteAdmin(admin.ModelAdmin):
    list_display = ("course", "value", "updated")
    list_filter = ("value",)
