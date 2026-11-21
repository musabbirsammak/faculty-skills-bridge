"""Proposed course edits: what changes, how to show it, and how to apply it once accepted."""
from .choices import AREA_NAMES
from .models import Course, CourseSkill, Skill

EDITABLE_FIELDS = ("title", "area", "description", "emerging", "impact", "impact_note", "source")


def changes_from(course, form, formset):
    """Only what the submitted form changes, or None if nothing does."""
    fields = {name: form.cleaned_data[name] for name in EDITABLE_FIELDS if form.cleaned_data[name] != getattr(course, name)}
    proposed = sorted(
        [f.cleaned_data["skill"].pk, bool(f.cleaned_data.get("core"))]
        for f in formset.forms
        if f.cleaned_data and f.cleaned_data.get("skill") and not f.cleaned_data.get("DELETE")
    )
    current = sorted([r.skill_id, r.core] for r in course.requirements.all())
    data = {"fields": fields}
    if proposed != current:
        data["requirements"] = proposed
    return data if fields or "requirements" in data else None


def _show(name, value):
    if name == "area":
        return f"{value} {AREA_NAMES.get(value, '')}".strip()
    if name == "emerging":
        return "Yes" if value else "No"
    return value if value not in ("", None) else "(empty)"


def describe(course, data):
    """Readable before/after for the review page, compared with the course as it is now."""
    labels = {f.name: str(f.verbose_name).capitalize() for f in Course._meta.fields}
    result = {
        "fields": [(labels[n], _show(n, getattr(course, n)), _show(n, v)) for n, v in data.get("fields", {}).items()],
        "added": [], "removed": [], "changed": [],
    }
    if "requirements" in data:
        current = {r.skill_id: r.core for r in course.requirements.all()}
        proposed = {sid: core for sid, core in data["requirements"]}
        names = Skill.objects.in_bulk(set(current) | set(proposed))
        result["added"] = [(names[s].name, proposed[s]) for s in proposed if s not in current and s in names]
        result["removed"] = [(names[s].name, current[s]) for s in current if s not in proposed and s in names]
        result["changed"] = [(names[s].name, proposed[s]) for s in proposed if s in current and current[s] != proposed[s]]
    return result


def apply_edit(edit):
    course = edit.course
    for name, value in edit.data.get("fields", {}).items():
        setattr(course, name, value)
    course.last_edited_by = edit.proposed_by
    course.save()
    if "requirements" in edit.data:
        proposed = {sid: core for sid, core in edit.data["requirements"]}
        course.requirements.exclude(skill_id__in=proposed).delete()
        existing = set(Skill.objects.filter(pk__in=proposed).values_list("pk", flat=True))
        for skill_id, core in proposed.items():
            if skill_id in existing:
                CourseSkill.objects.update_or_create(course=course, skill_id=skill_id, defaults={"core": core})
