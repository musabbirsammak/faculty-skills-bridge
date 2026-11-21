"""Shared engine for policy proposals and course redesigns: documents with editable sections,
a revision history for every section, typed comments, and stances."""
from django.conf import settings
from django.db import models
from django.urls import reverse

SECTION_TEMPLATES = {
    "policy": [
        ("Problem", "What is happening, and who does it affect? Use facts and numbers where you can."),
        ("Proposal", "What exactly should change? Be specific enough that someone could act on it."),
        ("Who is affected", "Students, teachers, staff, administration: how does each group gain or lose?"),
        ("How it would work", "Steps, timeline, responsibilities and resources."),
        ("Risks and open questions", "What could go wrong? What do we still not know?"),
    ],
    "redesign": [
        ("Why redesign", "What has changed in the field, in students or in the tools they use?"),
        ("Learning outcomes", "What should students be able to do by the end of the course?"),
        ("Weekly topics", "A week-by-week outline."),
        ("Assessment", "How will students show what they have learned, in ways AI cannot do for them?"),
        ("AI use policy", "When may students use AI tools, and how should they declare it?"),
        ("Skills a teacher needs", "Which skills does teaching this version require? Keep the catalogue in step."),
    ],
}

KIND_LABELS = {
    "policy": {
        "plural": "Policy proposals", "singular": "proposal", "new": "New proposal",
        "list_url": "deliberation:proposals", "create_url": "deliberation:proposal_create",
        "intro": "Draft proposals for the department together. Anyone can edit the text; every change is kept, "
                 "and comments sit next to the section they are about.",
    },
    "redesign": {
        "plural": "Course redesign studio", "singular": "redesign", "new": "New redesign",
        "list_url": "deliberation:studio", "create_url": "deliberation:redesign_create",
        "intro": "Rework a course for the AI era with colleagues. One person sees part of the picture; "
                 "many people together notice what a single designer would miss.",
    },
}


class Document(models.Model):
    class Kind(models.TextChoices):
        POLICY = "policy", "Policy proposal"
        REDESIGN = "redesign", "Course redesign"

    class Status(models.TextChoices):
        DRAFT = "draft", "Drafting"
        OPEN = "open", "Open for discussion"
        SUBMITTED = "submitted", "Submitted to department"
        ADOPTED = "adopted", "Adopted"
        CLOSED = "closed", "Closed"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    title = models.CharField(max_length=200)
    summary = models.TextField(help_text="Two or three sentences: what this is about and why it matters.")
    course = models.ForeignKey("catalog.Course", null=True, blank=True, on_delete=models.SET_NULL, related_name="redesigns")
    department = models.ForeignKey(
        "accounts.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="documents",
        help_text="Leave empty if it concerns the whole university.",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="documents")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("deliberation:detail", args=[self.pk])

    @property
    def labels(self):
        return KIND_LABELS[self.kind]

    def create_sections(self):
        for order, (title, prompt) in enumerate(SECTION_TEMPLATES[self.kind]):
            body = ""
            if self.kind == self.Kind.REDESIGN and title == "Skills a teacher needs" and self.course:
                body = "\n".join(
                    f"- {r.skill.name} ({'core' if r.core else 'supporting'})"
                    for r in self.course.requirements.select_related("skill")
                )
            Section.objects.create(document=self, title=title, prompt=prompt, order=order, body=body)

    def touch(self):
        self.save(update_fields=["updated"])

    def watchers(self):
        """Everyone involved: the author, editors, commenters and people who took a stance."""
        ids = {self.created_by_id}
        ids |= set(Revision.objects.filter(section__document=self).values_list("author_id", flat=True))
        ids |= set(self.comments.values_list("author_id", flat=True))
        ids |= set(self.stances.values_list("user_id", flat=True))
        return {i for i in ids if i}


class Section(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=120)
    prompt = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    body = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=0)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Revision(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="revisions")
    body = models.TextField(blank=True)
    note = models.CharField(max_length=200, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created", "id"]


class Comment(models.Model):
    class Kind(models.TextChoices):
        SUGGESTION = "suggestion", "Suggestion"
        SUPPORT = "support", "Support"
        CONCERN = "concern", "Concern"
        QUESTION = "question", "Question"

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="comments")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="comments")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.SUGGESTION)
    body = models.TextField()
    anonymous = models.BooleanField(default=False, help_text="Colleagues see 'A colleague' instead of your name.")
    resolved = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created", "id"]

    @property
    def shown_author(self):
        if self.anonymous:
            return "A colleague"
        return str(self.author) if self.author else "Former member"


class Stance(models.Model):
    class Value(models.TextChoices):
        SUPPORT = "support", "I support this"
        AMEND = "amend", "Support with changes"
        OPPOSE = "oppose", "I have concerns"

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="stances")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    value = models.CharField(max_length=10, choices=Value.choices)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["document", "user"], name="unique_stance")]
