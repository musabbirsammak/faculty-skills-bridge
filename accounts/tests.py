from django.test import TestCase
from django.urls import reverse

from catalog.scopes import allowed_scopes, visible_children

from .models import Department, Faculty, Institution, User

SIGNUP = {
    "display_name": "New Teacher", "username": "newteacher", "email": "new@example.edu",
    "designation": "Lecturer", "password1": "a-Long-pass-987", "password2": "a-Long-pass-987",
}


class InstitutionTests(TestCase):
    def test_only_allowed_domains_can_register(self):
        institution = Institution.load()
        institution.email_domains = "uni.edu"
        institution.save()
        response = self.client.post(reverse("accounts:signup"), SIGNUP)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newteacher").exists())
        self.client.post(reverse("accounts:signup"), {**SIGNUP, "email": "new@uni.edu"})
        self.assertTrue(User.objects.filter(username="newteacher").exists())

    def test_approval_keeps_new_accounts_inactive(self):
        institution = Institution.load()
        institution.require_approval = True
        institution.save()
        response = self.client.post(reverse("accounts:signup"), SIGNUP)
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(User.objects.get(username="newteacher").is_active)

    def test_institution_name_is_shown(self):
        institution = Institution.load()
        institution.name = "Example University"
        institution.save()
        self.assertContains(self.client.get(reverse("home")), "Example University")

    def test_privacy_page(self):
        self.assertContains(self.client.get(reverse("privacy")), "What can others see?")


class ScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fsit = Faculty.objects.create(name="Science", short_name="FSIT")
        cls.fbe = Faculty.objects.create(name="Business", short_name="FBE")
        cls.swe = Department.objects.create(faculty=cls.fsit, name="Software Engineering")
        cls.cse = Department.objects.create(faculty=cls.fsit, name="Computer Science")
        cls.bba = Department.objects.create(faculty=cls.fbe, name="Business Administration")

    def keys(self, user):
        return [s.key for s in allowed_scopes(user)]

    def test_teacher_sees_university_and_own_department(self):
        teacher = User.objects.create_user("t", password="x-Long-123", department=self.swe)
        self.assertEqual(self.keys(teacher), ["university", f"department-{self.swe.pk}"])

    def test_dean_sees_own_faculty_and_its_departments(self):
        dean = User.objects.create_user("d", password="x-Long-123", department=self.swe, role=User.Role.DEAN)
        keys = self.keys(dean)
        self.assertIn(f"faculty-{self.fsit.pk}", keys)
        self.assertIn(f"department-{self.cse.pk}", keys)
        self.assertNotIn(f"faculty-{self.fbe.pk}", keys)
        faculty_scope = next(s for s in allowed_scopes(dean) if s.kind == "faculty")
        self.assertEqual(len(visible_children(faculty_scope, allowed_scopes(dean))), 2)
        university = allowed_scopes(dean)[0]
        self.assertEqual(visible_children(university, allowed_scopes(dean)), [])

    def test_leadership_sees_everything(self):
        vc = User.objects.create_user("vc", password="x-Long-123", role=User.Role.LEADERSHIP)
        self.assertEqual(len(self.keys(vc)), 1 + 2 + 3)

    def test_who_can_set_course_status(self):
        from catalog.models import Course
        from catalog.scopes import can_set_status
        swe_course = Course.objects.create(title="SWE course", area="0613", department=self.swe)
        bba_course = Course.objects.create(title="BBA course", area="0413", department=self.bba)
        open_course = Course.objects.create(title="Unassigned", area="0613")
        teacher = User.objects.create_user("tt", password="x-Long-123", department=self.swe)
        head = User.objects.create_user("hh", password="x-Long-123", department=self.swe, role=User.Role.HEAD)
        dean = User.objects.create_user("dd", password="x-Long-123", department=self.cse, role=User.Role.DEAN)
        vc = User.objects.create_user("vv", password="x-Long-123", role=User.Role.LEADERSHIP)
        self.assertFalse(can_set_status(teacher, swe_course))
        self.assertTrue(can_set_status(head, swe_course))
        self.assertTrue(can_set_status(head, open_course))
        self.assertFalse(can_set_status(head, bba_course))
        self.assertTrue(can_set_status(dean, swe_course))      # same faculty
        self.assertFalse(can_set_status(dean, bba_course))
        self.assertTrue(can_set_status(vc, bba_course))

    def test_status_change_is_logged(self):
        from catalog.models import Course
        course = Course.objects.create(title="MLOps", area="0613")
        head = User.objects.create_user("h3", password="x-Long-123", department=self.swe, role=User.Role.HEAD)
        self.client.force_login(head)
        self.client.post(reverse("catalog:course_status", args=[course.pk]),
                         {"status": "planned", "department": self.swe.pk, "note": "Needed for accreditation"})
        course.refresh_from_db()
        self.assertEqual((course.status, course.department), ("planned", self.swe))
        self.assertEqual(course.status_changes.get().note, "Needed for accreditation")
        teacher = User.objects.create_user("t3", password="x-Long-123", department=self.swe)
        self.client.force_login(teacher)
        response = self.client.post(reverse("catalog:course_status", args=[course.pk]), {"status": "offered"})
        self.assertEqual(response.status_code, 403)

    def test_teacher_edits_become_proposals_until_accepted(self):
        from catalog.models import Course, CourseEdit, CourseSkill, Skill
        skill = Skill.objects.create(name="Software testing", family="prog")
        course = Course.objects.create(title="QA", area="0613", department=self.swe, impact=3)
        CourseSkill.objects.create(course=course, skill=skill, core=True)
        teacher = User.objects.create_user("t4", password="x-Long-123", department=self.swe)
        head = User.objects.create_user("h4", password="x-Long-123", department=self.swe, role=User.Role.HEAD)
        form = {
            "title": "QA", "area": "0613", "description": "", "impact": 5, "impact_note": "", "source": "",
            "requirements-TOTAL_FORMS": "1", "requirements-INITIAL_FORMS": "1",
            "requirements-MIN_NUM_FORMS": "0", "requirements-MAX_NUM_FORMS": "1000",
            "requirements-0-id": course.requirements.get().pk, "requirements-0-course": course.pk,
            "requirements-0-skill": skill.pk, "requirements-0-core": "on", "edit_note": "More demand",
        }
        self.client.force_login(teacher)
        self.client.post(reverse("catalog:course_edit", args=[course.pk]), form)
        course.refresh_from_db()
        self.assertEqual(course.impact, 3)                       # not applied yet
        edit = CourseEdit.objects.get()
        self.assertEqual(edit.data, {"fields": {"impact": 5}})   # only what changed
        self.assertTrue(head.notifications.filter(message__contains="proposed changes").exists())

        self.client.force_login(teacher)
        self.assertEqual(self.client.post(edit.get_absolute_url(), {"decision": "accept"}).status_code, 403)
        self.client.force_login(head)
        self.client.post(edit.get_absolute_url(), {"decision": "accept", "note": "Agreed"})
        course.refresh_from_db()
        edit.refresh_from_db()
        self.assertEqual((course.impact, edit.state), (5, "accepted"))
        self.assertTrue(teacher.notifications.filter(message__contains="accepted").exists())

    def test_votes_on_suggested_courses(self):
        from catalog.models import Course
        author = User.objects.create_user("a5", password="x-Long-123", department=self.swe)
        voter = User.objects.create_user("v5", password="x-Long-123", department=self.swe)
        course = Course.objects.create(title="Green Computing", area="0688", status="suggested", added_by=author)
        self.client.force_login(voter)
        url = reverse("catalog:course_vote", args=[course.pk])
        self.client.post(url, {"value": "support"})
        self.assertEqual(course.votes.get().value, "support")
        self.assertTrue(author.notifications.filter(message__contains="1 support").exists())
        self.client.post(url, {"value": "support"})            # clicking again withdraws
        self.assertFalse(course.votes.exists())
        course.status = "planned"
        course.save()
        self.client.post(url, {"value": "oppose"})
        self.assertFalse(course.votes.exists())                 # closed once no longer suggested

    def test_insights_ignore_scopes_outside_the_role(self):
        teacher = User.objects.create_user("t2", password="x-Long-123", department=self.swe)
        self.client.force_login(teacher)
        response = self.client.get(reverse("catalog:dashboard"), {"scope": f"faculty-{self.fbe.pk}"})
        self.assertEqual(response.context["scope"].key, "university")
