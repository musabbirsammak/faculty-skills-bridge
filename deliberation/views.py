import difflib
from collections import Counter, defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Course
from notifications.notify import notify

from .forms import CommentForm, DocumentForm, SectionAddForm, SectionEditForm
from .models import KIND_LABELS, Comment, Document, Revision, Section, Stance


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _can_manage(user, doc):
    return user.is_staff or doc.created_by_id == user.id


@login_required
def document_list(request, kind):
    status = request.GET.get("status", "")
    docs = (
        Document.objects.filter(kind=kind)
        .select_related("created_by", "course", "department")
        .annotate(n_comments=Count("comments", distinct=True), n_sections=Count("sections", distinct=True))
    )
    if status in Document.Status.values:
        docs = docs.filter(status=status)
    return render(request, "deliberation/document_list.html", {
        "docs": docs, "kind": kind, "labels": KIND_LABELS[kind],
        "statuses": Document.Status.choices, "status": status,
    })


@login_required
def document_create(request, kind):
    initial = {"department": request.user.department_id} if kind == Document.Kind.REDESIGN else {}
    course = Course.objects.filter(pk=_int(request.GET.get("course"))).first()
    if course:
        initial.update({"course": course, "title": f"{course.title}: a redesign"})
    form = DocumentForm(request.POST or None, kind=kind, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            doc = form.save(commit=False)
            doc.kind = kind
            doc.created_by = request.user
            doc.save()
            doc.create_sections()
        messages.success(request, "Created. Each section has a prompt to get you started; colleagues can now edit and comment.")
        return redirect(doc)
    return render(request, "deliberation/document_form.html", {"form": form, "labels": KIND_LABELS[kind], "doc": None})


@login_required
def document_edit(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if not _can_manage(request.user, doc):
        return HttpResponseForbidden("Only the author or an administrator can edit the title and summary.")
    form = DocumentForm(request.POST or None, instance=doc, kind=doc.kind)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(doc)
    return render(request, "deliberation/document_form.html", {"form": form, "labels": doc.labels, "doc": doc})


@login_required
def document_detail(request, pk):
    doc = get_object_or_404(Document.objects.select_related("course", "created_by"), pk=pk)
    sections = list(doc.sections.annotate(n_revisions=Count("revisions")).select_related("updated_by"))
    comments = (
        doc.comments.filter(parent__isnull=True)
        .select_related("author")
        .prefetch_related("replies__author")
    )
    show = request.GET.get("show", "")
    if show in Comment.Kind.values:
        comments = comments.filter(kind=show)
    by_section = defaultdict(list)
    for c in comments:
        by_section[c.section_id].append(c)
    for s in sections:
        s.thread = by_section.get(s.id, [])

    stance_counts = Counter(doc.stances.values_list("value", flat=True))
    total = sum(stance_counts.values())
    stances = [
        (value, label, stance_counts.get(value, 0), round(100 * stance_counts.get(value, 0) / total) if total else 0)
        for value, label in Stance.Value.choices
    ]
    my_stance = doc.stances.filter(user=request.user).values_list("value", flat=True).first()
    kind_counts = Counter(doc.comments.values_list("kind", flat=True))
    people = set(doc.comments.exclude(author=None).values_list("author_id", flat=True))
    people |= set(Revision.objects.filter(section__document=doc).exclude(author=None).values_list("author_id", flat=True))
    if doc.created_by_id:
        people.add(doc.created_by_id)

    section_id = _int(request.GET.get("section"))
    return render(request, "deliberation/document_detail.html", {
        "doc": doc,
        "sections": sections,
        "general": by_section.get(None, []),
        "stances": stances,
        "stance_total": total,
        "my_stance": my_stance,
        "comment_form": CommentForm(document=doc, initial={"section": section_id} if section_id else None),
        "reply_kinds": Comment.Kind.choices,
        "kind_counts": [(k, label, kind_counts.get(k, 0)) for k, label in Comment.Kind.choices],
        "show": show,
        "n_people": len(people),
        "can_manage": _can_manage(request.user, doc),
        "statuses": Document.Status.choices,
        "add_section_form": SectionAddForm(),
    })


@login_required
@require_POST
def document_status(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    status = request.POST.get("status")
    if _can_manage(request.user, doc) and status in Document.Status.values:
        doc.status = status
        doc.save(update_fields=["status", "updated"])
        notify(doc.watchers(), f"“{doc.title}” is now {doc.get_status_display().lower()}", doc.get_absolute_url(),
               exclude=request.user)
        messages.success(request, f"Status changed to {doc.get_status_display()}.")
    return redirect(doc)


@login_required
@require_POST
def stance(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    value = request.POST.get("value")
    current = Stance.objects.filter(document=doc, user=request.user).first()
    if current and current.value == value:
        current.delete()
    elif value in Stance.Value.values:
        Stance.objects.update_or_create(document=doc, user=request.user, defaults={"value": value})
    return redirect(f"{doc.get_absolute_url()}#stance")


@login_required
@require_POST
def comment_create(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    form = CommentForm(request.POST, document=doc)
    if not form.is_valid():
        messages.error(request, "Your comment was empty or incomplete. Please try again.")
        return redirect(doc)
    comment = form.save(commit=False)
    comment.document = doc
    comment.author = request.user
    parent = doc.comments.filter(pk=_int(request.POST.get("parent"))).first()
    if parent:
        comment.parent = parent.parent or parent  # one level of replies keeps threads readable
        comment.section = comment.parent.section
    comment.save()
    doc.touch()
    who = "A colleague" if comment.anonymous else str(request.user)
    action = "replied to a comment on" if comment.parent else f"added a {comment.get_kind_display().lower()} to"
    notify(doc.watchers(), f"{who} {action} “{doc.title}”", f"{doc.get_absolute_url()}#c{comment.pk}", exclude=request.user)
    return redirect(f"{doc.get_absolute_url()}#c{comment.pk}")


@login_required
@require_POST
def comment_resolve(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("document"), pk=pk)
    if _can_manage(request.user, comment.document) or comment.author_id == request.user.id:
        comment.resolved = not comment.resolved
        comment.save(update_fields=["resolved"])
    return redirect(f"{comment.document.get_absolute_url()}#c{comment.pk}")


@login_required
def section_edit(request, pk):
    section = get_object_or_404(Section.objects.select_related("document"), pk=pk)
    doc = section.document
    conflict = None
    form = SectionEditForm(request.POST or None, initial={"body": section.body, "base_version": section.version})
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["base_version"] != section.version:
            conflict = {"theirs": section.body, "by": section.updated_by}
            form = SectionEditForm(initial={
                "body": form.cleaned_data["body"], "note": form.cleaned_data["note"], "base_version": section.version,
            })
        else:
            with transaction.atomic():
                if not section.revisions.exists() and section.body:
                    Revision.objects.create(section=section, body=section.body, note="Starting text", author=doc.created_by)
                section.body = form.cleaned_data["body"]
                section.version += 1
                section.updated_by = request.user
                section.save()
                Revision.objects.create(section=section, body=section.body, note=form.cleaned_data["note"], author=request.user)
                doc.touch()
            notify(doc.watchers(), f"{request.user} edited “{section.title}” in “{doc.title}”",
                   f"{doc.get_absolute_url()}#s{section.pk}", exclude=request.user)
            messages.success(request, f"Saved “{section.title}”.")
            return redirect(f"{doc.get_absolute_url()}#s{section.pk}")
    return render(request, "deliberation/section_edit.html", {"section": section, "doc": doc, "form": form, "conflict": conflict})


def _line_diff(old, new):
    rows = []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        tag, text = line[:2], line[2:]
        if tag == "? ":
            continue
        rows.append(({"+ ": "add", "- ": "del"}.get(tag, "same"), text))
    return rows


@login_required
def section_history(request, pk):
    section = get_object_or_404(Section.objects.select_related("document"), pk=pk)
    revisions = list(section.revisions.select_related("author"))
    entries, previous = [], ""
    for rev in revisions:
        entries.append({"rev": rev, "diff": _line_diff(previous, rev.body)})
        previous = rev.body
    entries.reverse()
    return render(request, "deliberation/section_history.html", {"section": section, "doc": section.document, "entries": entries})


@login_required
@require_POST
def section_add(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    form = SectionAddForm(request.POST)
    if form.is_valid():
        last = doc.sections.aggregate(m=Max("order"))["m"] or 0
        section = Section.objects.create(document=doc, title=form.cleaned_data["title"], order=last + 1)
        doc.touch()
        return redirect("deliberation:section_edit", pk=section.pk)
    return redirect(doc)
