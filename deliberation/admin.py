from django.contrib import admin

from .models import Comment, Document, Revision, Section, Stance


class SectionInline(admin.StackedInline):
    model = Section
    extra = 0
    fields = ("title", "order", "prompt", "body")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "status", "department", "course", "created_by", "updated")
    list_filter = ("kind", "status", "department__faculty")
    search_fields = ("title", "summary")
    inlines = [SectionInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("document", "kind", "author", "anonymous", "resolved", "created")
    list_filter = ("kind", "anonymous", "resolved")


admin.site.register(Revision)
admin.site.register(Stance)
