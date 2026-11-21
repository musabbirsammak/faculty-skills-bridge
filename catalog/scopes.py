"""Which totals each role may see. Everything built on scopes shows aggregates only, never individuals."""
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.models import Department, Faculty, Institution


@dataclass
class Scope:
    key: str          # "university", "faculty-3", "department-7"
    label: str
    kind: str         # university | faculty | department
    obj: Any = None

    def members(self):
        users = get_user_model().objects.filter(is_active=True)
        if self.kind == "faculty":
            return users.filter(department__faculty=self.obj)
        if self.kind == "department":
            return users.filter(department=self.obj)
        return users

    def children(self):
        if self.kind == "university":
            return [_faculty(f) for f in Faculty.objects.all()]
        if self.kind == "faculty":
            return [_department(d) for d in self.obj.departments.all()]
        return []

    def documents(self, queryset):
        if self.kind == "faculty":
            return queryset.filter(department__faculty=self.obj)
        if self.kind == "department":
            return queryset.filter(department=self.obj)
        return queryset


def _faculty(faculty):
    return Scope(f"faculty-{faculty.pk}", faculty.name, "faculty", faculty)


def _department(department):
    return Scope(f"department-{department.pk}", f"{department.name} · {department.faculty.short_name or department.faculty.name}",
                 "department", department)


def allowed_scopes(user):
    """University first, then the faculties and departments this user's role may see."""
    scopes = [Scope("university", Institution.load().name, "university")]
    if user.is_staff or user.role == user.Role.LEADERSHIP:
        for faculty in Faculty.objects.prefetch_related("departments"):
            scopes.append(_faculty(faculty))
            scopes += [_department(d) for d in faculty.departments.all()]
    elif user.role == user.Role.DEAN and user.department_id:
        faculty = user.department.faculty
        scopes.append(_faculty(faculty))
        scopes += [_department(d) for d in faculty.departments.all()]
    elif user.department_id:
        scopes.append(_department(user.department))
    return scopes


def visible_children(scope, allowed):
    """Child units of a scope, only if the user may see every one of them."""
    keys = {s.key for s in allowed}
    children = scope.children()
    return children if children and all(c.key in keys for c in children) else []


def manageable_departments(user):
    """Departments whose courses this user may set the status of."""
    if user.is_staff or user.role == user.Role.LEADERSHIP:
        return Department.objects.all()
    if user.role == user.Role.DEAN and user.department_id:
        return Department.objects.filter(faculty=user.department.faculty)
    if user.role == user.Role.HEAD and user.department_id:
        return Department.objects.filter(pk=user.department_id)
    return Department.objects.none()


def can_set_status(user, course):
    """Leadership: any course. Deans and heads: courses of their units, or not yet assigned to a department."""
    if user.is_staff or user.role == user.Role.LEADERSHIP:
        return True
    if user.role not in (user.Role.HEAD, user.Role.DEAN) or not user.department_id:
        return False
    return course.department_id is None or manageable_departments(user).filter(pk=course.department_id).exists()


def course_in_scope(course, scope):
    """Courses of the scope's departments, plus courses no department owns yet."""
    if scope.kind == "university" or course.department_id is None:
        return True
    if scope.kind == "faculty":
        return course.department.faculty_id == scope.obj.pk
    return course.department_id == scope.obj.pk


def course_approvers(course, fallback_department=None):
    """People who can decide on this course: leadership, staff, and the heads and deans responsible for it."""
    User = get_user_model()
    department = course.department or fallback_department
    query = Q(role=User.Role.LEADERSHIP) | Q(is_staff=True)
    if department:
        query |= Q(role=User.Role.HEAD, department=department) | Q(role=User.Role.DEAN, department__faculty=department.faculty)
    return User.objects.filter(query, is_active=True)


def course_watchers(course):
    """Everyone involved with a course: who added or edited it, voted on it, proposed changes or decided its status."""
    ids = {course.added_by_id, course.last_edited_by_id}
    ids |= set(course.votes.values_list("user_id", flat=True))
    ids |= set(course.edits.values_list("proposed_by_id", flat=True))
    ids |= set(course.status_changes.values_list("changed_by_id", flat=True))
    return {i for i in ids if i}
