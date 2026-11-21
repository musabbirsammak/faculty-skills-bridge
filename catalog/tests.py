from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Course, CourseSkill, Feedback, Skill, TeacherSkill


class CatalogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.testing = Skill.objects.create(name="Software testing", family="prog")
        cls.automation = Skill.objects.create(name="Test automation", family="prog")
        cls.evaluation = Skill.objects.create(name="Model evaluation", family="ai")
        cls.evaluation.related.add(cls.testing)
        cls.qa = Course.objects.create(title="Quality Assurance", area="0613", impact=3)
        CourseSkill.objects.create(course=cls.qa, skill=cls.testing, core=True)
        CourseSkill.objects.create(course=cls.qa, skill=cls.automation, core=True)
        cls.ai = Course.objects.create(title="Testing AI Systems", area="0613", impact=5, emerging=True)
        CourseSkill.objects.create(course=cls.ai, skill=cls.evaluation, core=True)
        CourseSkill.objects.create(course=cls.ai, skill=cls.testing, core=True)
        cls.user = User.objects.create_user("teacher1", password="pw-Long-12345", display_name="Teacher One")

    def setUp(self):
        self.client.force_login(self.user)

    def test_signup_logs_in(self):
        self.client.logout()
        response = self.client.post(reverse("accounts:signup"), {
            "display_name": "New Teacher", "username": "newteacher", "email": "new@example.com",
            "designation": "Lecturer",
            "password1": "a-Long-pass-987", "password2": "a-Long-pass-987",
        })
        self.assertRedirects(response, reverse("catalog:my_skills"))

    def test_pages_require_login(self):
        self.client.logout()
        response = self.client.get(reverse("catalog:suggestions"))
        self.assertEqual(response.status_code, 302)

    def test_add_skills_then_see_suggestions(self):
        url = reverse("catalog:my_skills")
        self.client.post(url, {"action": "add", "skill": self.testing.id, "level": "teach"})
        self.client.post(url, {"action": "add", "skill": self.automation.id, "level": "teach"})
        self.assertEqual(TeacherSkill.objects.filter(teacher=self.user).count(), 2)
        response = self.client.get(reverse("catalog:suggestions"))
        self.assertContains(response, "Quality Assurance")
        self.assertContains(response, "Testing AI Systems")  # reachable through the related skill

    def test_explore_shows_courses_out_of_reach(self):
        TeacherSkill.objects.create(teacher=self.user, skill=self.automation, level="fam")
        far = Course.objects.create(title="Statistics for Nurses", area="0913")  # health field
        CourseSkill.objects.create(course=far, skill=self.evaluation, core=True)
        response = self.client.get(reverse("catalog:suggestions"), {"explore": "health"})
        self.assertContains(response, "Statistics for Nurses")
        self.assertNotContains(response, "Quality Assurance")  # different field

    def test_feedback_toggles(self):
        url = reverse("catalog:feedback", args=[self.qa.id])
        first = self.client.post(url, {"response": "fit"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(first.json()["response"], "fit")
        second = self.client.post(url, {"response": "fit"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(second.json()["response"], "")
        self.assertFalse(Feedback.objects.exists())

    def test_create_course_with_skills(self):
        data = {
            "title": "New Course", "area": "0613", "description": "", "impact": 4, "impact_note": "", "source": "",
            "requirements-TOTAL_FORMS": "4", "requirements-INITIAL_FORMS": "0",
            "requirements-MIN_NUM_FORMS": "0", "requirements-MAX_NUM_FORMS": "1000",
            "requirements-0-skill": self.testing.id, "requirements-0-core": "on",
        }
        response = self.client.post(reverse("catalog:course_create"), data)
        course = Course.objects.get(title="New Course")
        self.assertRedirects(response, course.get_absolute_url())
        self.assertEqual(course.requirements.count(), 1)
        self.assertEqual(course.added_by, self.user)
        self.assertEqual(course.status, "suggested")  # teachers' new courses start as suggestions
        self.assertEqual(course.field, "ict")  # derived from the ISCED-F area

    def test_field_follows_area(self):
        course = Course.objects.create(title="Statistics", area="0542")
        self.assertEqual(course.field, "natural")

    def test_course_needs_a_core_skill(self):
        data = {
            "title": "No Core", "area": "0613", "impact": 3,
            "requirements-TOTAL_FORMS": "1", "requirements-INITIAL_FORMS": "0",
            "requirements-MIN_NUM_FORMS": "0", "requirements-MAX_NUM_FORMS": "1000",
            "requirements-0-skill": self.testing.id,
        }
        response = self.client.post(reverse("catalog:course_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Course.objects.filter(title="No Core").exists())

    def test_dashboard_hides_small_numbers(self):
        TeacherSkill.objects.create(teacher=self.user, skill=self.testing, level="teach")
        TeacherSkill.objects.create(teacher=self.user, skill=self.automation, level="teach")
        response = self.client.get(reverse("catalog:dashboard"))
        self.assertContains(response, "&lt;3")
        self.assertEqual(response.context["needs"], [])
