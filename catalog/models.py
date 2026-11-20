from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from .choices import AREA_CHOICES, AREA_NAMES, AREA_TO_FIELD, FieldOfStudy


class Skill(models.Model):
    class Family(models.TextChoices):
        PROGRAMMING = "prog", "Programming & software engineering"
        DATA = "data", "Data & databases"
        MATH = "math", "Mathematics & statistics"
        AI = "ai", "AI & machine learning"
        SYSTEMS = "sys", "Systems & infrastructure"
        SECURITY = "sec", "Security"
        SUSTAINABILITY = "green", "Sustainability"
        BUSINESS = "biz", "Business & management"
        FINANCE = "fin", "Accounting & finance"
        MARKETING = "mkt", "Marketing & sales"
        PEOPLE = "ppl", "People, society & teaching"
        OTHER = "other", "Other"

    name = models.CharField(max_length=160, unique=True)
    family = models.CharField(max_length=10, choices=Family.choices, default=Family.OTHER)
    aliases = models.TextField(blank=True, help_text="Other names, separated by commas. Used by search.")
    description = models.TextField(blank=True)
    related = models.ManyToManyField("self", blank=True, help_text="Close skills that give partial credit.")
    esco_uri = models.URLField(max_length=255, blank=True, verbose_name="ESCO URI")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def alias_list(self):
        return [a.strip() for a in self.aliases.split(",") if a.strip()]


class Course(models.Model):
    class Status(models.TextChoices):
        CATALOGUE = "catalogue", "In the catalogue"
        SUGGESTED = "suggested", "Suggested"
        PLANNED = "planned", "Planned"
        OFFERED = "offered", "Offered here"
        RETIRING = "retiring", "Retiring"

    title = models.CharField(max_length=160, unique=True)
    area = models.CharField(
        max_length=80, choices=AREA_CHOICES,
        help_text="The ISCED-F 2013 detailed field that best describes the course content.",
    )
    field = models.CharField(
        max_length=12, choices=FieldOfStudy.choices, default=FieldOfStudy.ICT, editable=False,
        help_text="Broad field of education. Set automatically from the area.",
    )
    description = models.TextField(blank=True)
    emerging = models.BooleanField(default=False, help_text="A recent subject departments are adding (AI era, sustainability).")
    impact = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 to 5. Expected demand and value of the subject over the next five years.",
    )
    impact_note = models.CharField(max_length=255, blank=True, help_text="Why this rating, in one sentence.")
    source = models.CharField(max_length=255, blank=True, help_text="Where the rating comes from.")
    skills = models.ManyToManyField(Skill, through="CourseSkill", related_name="courses")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.CATALOGUE,
        help_text="Whether this university offers, plans or is retiring the course. Set by heads, deans and leadership.",
    )
    department = models.ForeignKey(
        "accounts.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="courses",
        help_text="The department that offers, plans or is retiring it.",
    )
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    last_edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("catalog:course_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        self.field = AREA_TO_FIELD.get(self.area, self.field)
        super().save(*args, **kwargs)

    @property
    def area_name(self):
        """The detailed field's name without its code, for labels."""
        return AREA_NAMES.get(self.area, self.area)


class CourseStatusChange(models.Model):
    """History of status decisions, shown on the course page."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="status_changes")
    old_status = models.CharField(max_length=12, choices=Course.Status.choices)
    new_status = models.CharField(max_length=12, choices=Course.Status.choices)
    department = models.ForeignKey("accounts.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]


class CourseSkill(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="requirements")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="+")
    core = models.BooleanField(default=True, help_text="Core skills count three times as much as supporting ones.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["course", "skill"], name="unique_course_skill")]
        ordering = ["-core", "skill__name"]


class TeacherSkill(models.Model):
    class Level(models.TextChoices):
        TEACH = "teach", "Can teach it"
        USE = "use", "Use it regularly"
        FAMILIAR = "fam", "Familiar"

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="+")
    level = models.CharField(max_length=5, choices=Level.choices, default=Level.USE)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["teacher", "skill"], name="unique_teacher_skill")]
        ordering = ["skill__name"]


class Feedback(models.Model):
    """A teacher's reaction to a suggested course path. Only totals are shown to others."""

    class Response(models.TextChoices):
        FITS = "fit", "Makes sense"
        DOES_NOT_FIT = "nofit", "Doesn't fit"
        INTERESTED = "interested", "Interested"

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="feedback")
    response = models.CharField(max_length=12, choices=Response.choices)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["teacher", "course"], name="unique_feedback")]


class CourseVote(models.Model):
    """Support or opposition for a suggested course. Only totals are shown."""

    class Value(models.TextChoices):
        SUPPORT = "support", "Support"
        OPPOSE = "oppose", "Oppose"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    value = models.CharField(max_length=8, choices=Value.choices)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["course", "user"], name="unique_course_vote")]


class CourseEdit(models.Model):
    """A proposed change to a course, decided by heads, deans or leadership.

    `data` holds only what changes: {"fields": {name: new value}, "requirements": [[skill_id, core], ...] or absent}.
    """

    class State(models.TextChoices):
        PENDING = "pending", "Waiting for review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Not accepted"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="edits")
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    data = models.JSONField()
    note = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    decision_note = models.CharField(max_length=255, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def get_absolute_url(self):
        return reverse("catalog:edit_review", args=[self.pk])
