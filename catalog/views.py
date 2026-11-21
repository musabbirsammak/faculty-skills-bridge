from collections import Counter, defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from deliberation.models import Document
from notifications.notify import notify

from .choices import AREA_NAMES, FieldOfStudy
from .forms import CourseForm, CourseStatusForm, RequirementFormSetFactory, SkillForm
from .matching import STRONG, TIER_ORDER, evaluate
from .edits import apply_edit, changes_from, describe
from .models import Course, CourseEdit, CourseStatusChange, CourseVote, Feedback, Skill, TeacherSkill
from .scopes import (
    allowed_scopes, can_set_status, course_approvers, course_in_scope, course_watchers, manageable_departments,
    visible_children,
)
from .services import explore_for, levels_for, load_catalog, suggestions_for

TIER_INFO = {
    "ready": ("Ready now", "You already cover most of what these courses need."),
    "short": ("Short preparation", "A few skills to add, usually within a semester."),
    "stretch": ("Stretch", "A bigger gap, but a realistic direction to grow."),
}


def _int(value):
    """Parse an id from user input; 0 (matches nothing) if it is not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _field(request):
    """The field-of-study filter from the query string, or '' for all fields."""
    value = request.GET.get("field", "")
    return value if value in FieldOfStudy.values else ""


def _safe_next(request, fallback):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return fallback


@login_required
def my_skills(request):
    if request.method == "POST":
        action = request.POST.get("action")
        level = request.POST.get("level", TeacherSkill.Level.USE)
        if level not in TeacherSkill.Level.values:
            level = TeacherSkill.Level.USE
        if action == "add":
            skill = Skill.objects.filter(pk=_int(request.POST.get("skill"))).first()
            if skill:
                TeacherSkill.objects.update_or_create(teacher=request.user, skill=skill, defaults={"level": level})
                messages.success(request, f"Added {skill.name}.")
            else:
                messages.error(request, "Pick a skill from the list, or propose a new one.")
        elif action == "level":
            TeacherSkill.objects.filter(teacher=request.user, pk=_int(request.POST.get("id"))).update(level=level)
        elif action == "remove":
            TeacherSkill.objects.filter(teacher=request.user, pk=_int(request.POST.get("id"))).delete()
        return redirect("catalog:my_skills")

    mine = request.user.skills.select_related("skill")
    owned = {ts.skill_id for ts in mine}
    all_skills = list(Skill.objects.all())
    families = defaultdict(list)
    for s in all_skills:
        families[s.get_family_display()].append((s, s.id in owned))
    return render(request, "catalog/my_skills.html", {
        "mine": mine,
        "levels": TeacherSkill.Level.choices,
        "families": sorted(families.items()),
        "skill_data": [
            {"id": s.id, "name": s.name, "family": s.get_family_display(), "aliases": s.alias_list()}
            for s in all_skills if s.id not in owned
        ],
    })


@login_required
def suggestions(request):
    emerging_only = request.GET.get("emerging") == "1"
    field = _field(request)
    explore_field = request.GET.get("explore", "")
    if explore_field not in FieldOfStudy.values:
        explore_field = ""
    if explore_field:
        cards, priorities = explore_for(request.user, explore_field)
    else:
        cards, priorities = suggestions_for(request.user, emerging_only=emerging_only, field=field)
    tiers = {t: [] for t in TIER_ORDER}
    for card in cards:
        if card["match"].tier:
            tiers[card["match"].tier].append(card)
    responses = dict(Feedback.objects.filter(teacher=request.user).values_list("course_id", "response"))
    for card in cards:
        card["response"] = responses.get(card["course"].id)
    return render(request, "catalog/suggestions.html", {
        "explore_field": explore_field,
        "explore_label": FieldOfStudy(explore_field).label if explore_field else "",
        "explore_cards": cards if explore_field else [],
        "tiers": [(t, TIER_INFO[t][0], TIER_INFO[t][1], tiers[t]) for t in TIER_ORDER],
        "priorities": priorities,
        "emerging_only": emerging_only,
        "field": field,
        "fields": FieldOfStudy.choices,
        "skill_count": request.user.skills.count(),
        "feedback_choices": Feedback.Response.choices,
    })


@login_required
@require_POST
def feedback(request, pk):
    course = get_object_or_404(Course, pk=pk)
    value = request.POST.get("response")
    current = Feedback.objects.filter(teacher=request.user, course=course).first()
    if current and current.response == value:
        current.delete()
        value = ""
    elif value in Feedback.Response.values:
        Feedback.objects.update_or_create(teacher=request.user, course=course, defaults={"response": value})
    else:
        value = current.response if current else ""
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"response": value})
    return redirect(_safe_next(request, "catalog:suggestions"))


@login_required
def course_list(request):
    q = request.GET.get("q", "").strip()
    area = request.GET.get("area", "")
    emerging = request.GET.get("emerging") == "1"
    field = _field(request)
    status = request.GET.get("status", "")
    courses = Course.objects.annotate(n_skills=Count("requirements"))
    if status in Course.Status.values:
        courses = courses.filter(status=status)
    if field:
        courses = courses.filter(field=field)
    if q:
        courses = courses.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(skills__name__icontains=q)).distinct()
    if area:
        courses = courses.filter(area=area)
    if emerging:
        courses = courses.filter(emerging=True)
    catalog, related = load_catalog()
    levels = levels_for(request.user)
    by_id = {c.id: c for c in catalog}
    match = {cid: evaluate(c, levels, related).percent for cid, c in by_id.items() if c.requirements} if levels else {}
    rows = [(c, match.get(c.id)) for c in courses.order_by("-emerging", "-impact", "title")]
    return render(request, "catalog/course_list.html", {
        "rows": rows,
        "areas": [(a, f"{a} {AREA_NAMES.get(a, '')}".strip())
                  for a in Course.objects.order_by("area").values_list("area", flat=True).distinct()],
        "q": q, "area": area, "emerging": emerging, "field": field, "fields": FieldOfStudy.choices,
        "status": status, "statuses": Course.Status.choices,
    })


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    catalog, related = load_catalog()
    course_input = next((c for c in catalog if c.id == course.pk), None)
    levels = levels_for(request.user)
    my_match = evaluate(course_input, levels, related) if levels and course_input and course_input.requirements else None
    counts = Counter(course.feedback.values_list("response", flat=True))
    total = sum(counts.values())
    show_feedback = total >= settings.PRIVACY_MIN_GROUP
    level_labels = dict(TeacherSkill.Level.choices)
    return render(request, "catalog/course_detail.html", {
        "course": course,
        "requirements": [(r, level_labels.get(levels.get(r.skill_id))) for r in course.requirements.select_related("skill")],
        "my_match": my_match,
        "feedback_rows": [(label, counts.get(value, 0)) for value, label in Feedback.Response.choices] if show_feedback else None,
        "feedback_total": total,
        "min_group": settings.PRIVACY_MIN_GROUP,
        "redesigns": course.redesigns.all(),
        "history": course.status_changes.select_related("changed_by", "department")[:8],
        "votes": Counter(course.votes.values_list("value", flat=True)),
        "my_vote": course.votes.filter(user=request.user).values_list("value", flat=True).first(),
        "pending_edits": course.edits.filter(state=CourseEdit.State.PENDING).select_related("proposed_by"),
        "can_set_status": can_set_status(request.user, course),
        "status_form": CourseStatusForm(
            departments=manageable_departments(request.user),
            initial={"status": course.status, "department": course.department_id},
        ),
    })


@login_required
@require_POST
def course_status(request, pk):
    """Heads, deans and leadership decide whether a course is suggested, planned, offered or retiring."""
    course = get_object_or_404(Course, pk=pk)
    if not can_set_status(request.user, course):
        return HttpResponseForbidden("Only heads, deans and university leadership can change a course's status.")
    form = CourseStatusForm(request.POST, departments=manageable_departments(request.user))
    if not form.is_valid():
        messages.error(request, "Choose a status, and a department you are responsible for.")
        return redirect(course)
    new_status, department = form.cleaned_data["status"], form.cleaned_data["department"]
    if new_status != course.status or department != course.department:
        CourseStatusChange.objects.create(
            course=course, old_status=course.status, new_status=new_status, department=department,
            changed_by=request.user, note=form.cleaned_data["note"],
        )
        course.status, course.department = new_status, department
        course.save(update_fields=["status", "department", "updated"])
        notify(course_watchers(course), f"{request.user} changed “{course.title}” to {course.get_status_display()}",
               f"{course.get_absolute_url()}#status", exclude=request.user)
        messages.success(request, f"Status changed to {course.get_status_display()}.")
    return redirect(course)


def _save_course(request, course=None):
    """New courses start as suggestions. Edits by heads, deans and leadership apply at once; others are proposed for review."""
    direct = course is None or can_set_status(request.user, course)
    original = Course.objects.get(pk=course.pk) if course else None  # form validation changes `course` in memory
    form = CourseForm(request.POST or None, instance=course)
    formset = RequirementFormSetFactory(request.POST or None, instance=course or Course())
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        if not direct:
            data = changes_from(original, form, formset)
            if data is None:
                messages.info(request, "You didn't change anything.")
                return redirect(original)
            edit = CourseEdit.objects.create(course=original, proposed_by=request.user, data=data,
                                             note=request.POST.get("edit_note", "").strip()[:255])
            recipients = set(course_approvers(original, request.user.department).values_list("pk", flat=True))
            notify(recipients | course_watchers(original), f"{request.user} proposed changes to “{original.title}”",
                   edit.get_absolute_url(), exclude=request.user)
            messages.success(request, "Your changes were sent for review. You'll be notified of the decision.")
            return redirect(edit)
        with transaction.atomic():
            obj = form.save(commit=False)
            created = not obj.pk
            if created:
                obj.added_by = request.user
                obj.status = Course.Status.SUGGESTED
            obj.last_edited_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
        if created:
            notify(course_approvers(obj, request.user.department), f"{request.user} suggested a new course: “{obj.title}”",
                   obj.get_absolute_url(), exclude=request.user)
        else:
            notify(course_watchers(obj), f"{request.user} updated “{obj.title}”", obj.get_absolute_url(), exclude=request.user)
        messages.success(request, "Course saved. Matches now use the updated skills.")
        return redirect(obj)
    return render(request, "catalog/course_form.html", {"form": form, "formset": formset, "course": course, "direct": direct})


@login_required
@require_POST
def course_vote(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if course.status != Course.Status.SUGGESTED:
        messages.info(request, "Voting is open only while a course is a suggestion.")
        return redirect(course)
    value = request.POST.get("value")
    current = CourseVote.objects.filter(course=course, user=request.user).first()
    if current and current.value == value:
        current.delete()
    elif value in CourseVote.Value.values:
        CourseVote.objects.update_or_create(course=course, user=request.user, defaults={"value": value})
    counts = Counter(course.votes.values_list("value", flat=True))
    notify([course.added_by_id],
           f"Your suggestion “{course.title}” now has {counts['support']} support and {counts['oppose']} oppose",
           f"{course.get_absolute_url()}#votes", exclude=request.user)
    return redirect(f"{course.get_absolute_url()}#votes")


@login_required
def edit_review(request, pk):
    edit = get_object_or_404(CourseEdit.objects.select_related("course", "proposed_by", "decided_by"), pk=pk)
    course = edit.course
    can_decide = edit.state == CourseEdit.State.PENDING and can_set_status(request.user, course)
    if request.method == "POST":
        decision = request.POST.get("decision")
        if not can_decide or decision not in ("accept", "reject"):
            return HttpResponseForbidden("Only heads, deans and leadership responsible for this course can decide.")
        if decision == "accept":
            new_title = edit.data.get("fields", {}).get("title")
            if new_title and Course.objects.exclude(pk=course.pk).filter(title=new_title).exists():
                messages.error(request, "Another course already has that title. Ask the proposer to choose a different one.")
                return redirect(edit)
            with transaction.atomic():
                apply_edit(edit)
                edit.state = CourseEdit.State.ACCEPTED
        else:
            edit.state = CourseEdit.State.REJECTED
        edit.decided_by, edit.decided_at = request.user, timezone.now()
        edit.decision_note = request.POST.get("note", "").strip()[:255]
        edit.save()
        verb = "accepted" if edit.state == CourseEdit.State.ACCEPTED else "did not accept"
        notify({edit.proposed_by_id} | course_watchers(course), f"{request.user} {verb} the proposed changes to “{course.title}”",
               edit.get_absolute_url(), exclude=request.user)
        messages.success(request, f"Changes {edit.get_state_display().lower()}.")
        return redirect(edit)
    return render(request, "catalog/edit_review.html", {"edit": edit, "diff": describe(course, edit.data), "can_decide": can_decide})


@login_required
def edit_list(request):
    pending = CourseEdit.objects.filter(state=CourseEdit.State.PENDING).select_related("course", "proposed_by")
    return render(request, "catalog/edit_list.html", {
        "to_decide": [e for e in pending if can_set_status(request.user, e.course)],
        "mine": CourseEdit.objects.filter(proposed_by=request.user).select_related("course")[:20],
    })


@login_required
def course_create(request):
    return _save_course(request)


@login_required
def course_edit(request, pk):
    return _save_course(request, get_object_or_404(Course, pk=pk))


@login_required
def skill_create(request):
    form = SkillForm(request.POST or None, initial={"name": request.GET.get("name", "")})
    if request.method == "POST" and form.is_valid():
        skill = form.save(commit=False)
        skill.added_by = request.user
        skill.save()
        form.save_m2m()
        messages.success(request, f"{skill.name} added to the skill list.")
        return redirect(_safe_next(request, "catalog:my_skills"))
    return render(request, "catalog/skill_form.html", {"form": form, "next": request.GET.get("next", "")})


def _levels_by_teacher(members):
    teachers = defaultdict(dict)
    for teacher_id, skill_id, level in TeacherSkill.objects.filter(teacher__in=members).values_list("teacher_id", "skill_id", "level"):
        teachers[teacher_id][skill_id] = level
    return teachers


def _aggregate(teachers, catalog, related):
    """Tier counts per course and weighted skill needs for recent subjects, over a group of teachers."""
    tier_counts, need = defaultdict(Counter), Counter()
    for levels in teachers.values():
        for c in catalog:
            if not c.requirements:
                continue
            m = evaluate(c, levels, related)
            if m.tier:
                tier_counts[c.id][m.tier] += 1
            if c.emerging and m.tier in ("short", "stretch"):
                for item in m.items:
                    if item.credit < STRONG:
                        need[item.skill_id] += item.weight * (1 - item.credit)
    return tier_counts, need


@login_required
def dashboard(request):
    """Insights for a university, faculty or department: totals only, with small numbers hidden."""
    min_group = settings.PRIVACY_MIN_GROUP
    field = _field(request)
    scopes = allowed_scopes(request.user)
    scope = next((s for s in scopes if s.key == request.GET.get("scope")), scopes[0])
    members = scope.members()
    catalog, related = load_catalog(field)
    emerging_ids = {c.id for c in catalog if c.emerging}

    teachers = _levels_by_teacher(members)
    tier_counts, need = _aggregate(teachers, catalog, related)
    enough = len(teachers) >= min_group

    def mask(n):
        return n if n == 0 or n >= min_group else f"<{min_group}"

    fb = defaultdict(Counter)
    for row in Feedback.objects.filter(teacher__in=members).values("course_id", "response").annotate(n=Count("id")):
        fb[row["course_id"]][row["response"]] = row["n"]

    rows = []
    course_rows = (Course.objects.filter(field=field) if field else Course.objects.all()).select_related("department")
    for course in course_rows.order_by("-emerging", "-impact", "title"):
        counts, votes = tier_counts[course.id], fb[course.id]
        total_votes = sum(votes.values())
        rows.append({
            "course": course,
            "ready": mask(counts["ready"]),
            "short": mask(counts["short"]),
            "stretch": mask(counts["stretch"]),
            "ready_raw": counts["ready"],
            "fit_share": round(100 * votes["fit"] / total_votes) if total_votes >= min_group else None,
            "interested": mask(votes["interested"]),
        })

    votes = Counter(CourseVote.objects.filter(course__status=Course.Status.SUGGESTED).values_list("course_id", "value"))
    for r in rows:
        r["support"], r["oppose"] = votes.get((r["course"].id, "support"), 0), votes.get((r["course"].id, "oppose"), 0)

    breakdown = []
    for child in visible_children(scope, scopes):
        child_members = child.members()
        child_teachers = _levels_by_teacher(child_members)
        child_enough = len(child_teachers) >= min_group
        child_tiers, child_need = _aggregate(child_teachers, catalog, related) if child_enough else ({}, Counter())
        top = child_need.most_common(1)
        breakdown.append({
            "scope": child,
            "registered": child_members.count(),
            "with_skills": len(child_teachers),
            "enough": child_enough,
            "recent_covered": sum(1 for cid in emerging_ids if child_tiers.get(cid, {}).get("ready")),
            "top_need": Skill.objects.filter(pk=top[0][0]).first() if top else None,
        })

    docs = scope.documents(Document.objects.all())
    doc_counts = Counter(docs.values_list("kind", "status"))
    doc_rows = [(label, doc_counts.get(("policy", value), 0), doc_counts.get(("redesign", value), 0))
                for value, label in Document.Status.choices]

    skill_map = Skill.objects.in_bulk([s for s, _ in need.most_common(8)])
    top_need = max(need.values(), default=1)
    return render(request, "catalog/dashboard.html", {
        "scopes": scopes,
        "scope": scope,
        "rows": rows,
        "registered": members.count(),
        "n_teachers": len(teachers),
        "responded": Feedback.objects.filter(teacher__in=members).values("teacher").distinct().count(),
        "enough": enough,
        "min_group": min_group,
        "field": field,
        "fields": FieldOfStudy.choices,
        "coverage_gaps": [r for r in rows if r["course"].emerging and r["ready_raw"] == 0][:8] if enough else [],
        "needs": [(skill_map[s], round(100 * v / top_need)) for s, v in need.most_common(8)] if enough else [],
        "breakdown": breakdown,
        "doc_rows": doc_rows,
        "adopted": docs.filter(status=Document.Status.ADOPTED).order_by("-updated")[:5],
        "planned": [r for r in rows if r["course"].status == Course.Status.PLANNED and course_in_scope(r["course"], scope)],
        "retiring": [r for r in rows if r["course"].status == Course.Status.RETIRING and course_in_scope(r["course"], scope)],
        "suggested": [r for r in rows if r["course"].status == Course.Status.SUGGESTED and course_in_scope(r["course"], scope)],
    })
