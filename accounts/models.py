from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from catalog.choices import FieldOfStudy


class Institution(models.Model):
    """The university running this installation. There is exactly one row."""

    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=40, blank=True)
    logo_url = models.CharField(
        max_length=300, blank=True,
        help_text="Address of a logo image: a full URL, or a path under /static/ if you add the file to the static folder.",
    )
    email_domains = models.CharField(
        max_length=300, blank=True,
        help_text="Only these email domains may register, separated by commas (e.g. diu.edu.bd). Leave empty to allow any.",
    )
    require_approval = models.BooleanField(
        default=False, help_text="New accounts stay inactive until an administrator activates them.",
    )
    contact_email = models.EmailField(blank=True, help_text="Shown to teachers who need help with their account.")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"name": settings.INSTITUTION_NAME})
        return obj

    def domain_list(self):
        return [d.strip().lower().lstrip("@") for d in self.email_domains.split(",") if d.strip()]


class Faculty(models.Model):
    name = models.CharField(max_length=160, unique=True)
    short_name = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "faculties"

    def __str__(self):
        return self.name


class Department(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=160)
    short_name = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["faculty__name", "name"]
        constraints = [models.UniqueConstraint(fields=["faculty", "name"], name="unique_department")]

    def __str__(self):
        return f"{self.name} ({self.faculty.short_name or self.faculty.name})"


class User(AbstractUser):
    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        HEAD = "head", "Head of department"
        DEAN = "dean", "Dean"
        LEADERSHIP = "leadership", "University leadership"

    display_name = models.CharField(max_length=80, help_text="How colleagues see you in discussions.")
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="members")
    designation = models.CharField(max_length=80, blank=True, help_text="e.g. Lecturer, Assistant Professor")
    field = models.CharField(
        max_length=12, choices=FieldOfStudy.choices, blank=True, default="",
        verbose_name="Main field", help_text="Used to point out course paths outside your field.",
    )
    role = models.CharField(
        max_length=12, choices=Role.choices, default=Role.TEACHER,
        help_text="Heads and deans see totals for their department or faculty; leadership sees all units. "
                  "No role can see an individual's skills.",
    )

    def __str__(self):
        return self.display_name or self.username

    @property
    def faculty(self):
        return self.department.faculty if self.department_id else None
