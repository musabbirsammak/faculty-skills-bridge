from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from catalog.models import Course, CourseSkill, Skill

from .models import Comment, Document


class DeliberationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", password="pw-Long-12345", display_name="Alice Rahman")
        cls.bob = User.objects.create_user("bob", password="pw-Long-12345", display_name="Bob Karim")
        skill = Skill.objects.create(name="Software testing", family="prog")
        cls.course = Course.objects.create(title="Quality Assurance", area="0613")
        CourseSkill.objects.create(course=cls.course, skill=skill, core=True)

    def make_doc(self, author):
        doc = Document.objects.create(kind="policy", title="Transition plans", summary="Why", created_by=author)
        doc.create_sections()
        return doc

    def test_policy_gets_template_sections(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("deliberation:proposal_create"), {"title": "P1", "summary": "S"})
        doc = Document.objects.get(title="P1")
        self.assertRedirects(response, doc.get_absolute_url())
        self.assertEqual(doc.sections.count(), 5)

    def test_redesign_prefills_teacher_skills(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("deliberation:redesign_create"), {"title": "R1", "summary": "S", "course": self.course.id})
        section = Document.objects.get(title="R1").sections.get(title="Skills a teacher needs")
        self.assertIn("Software testing (core)", section.body)

    def test_edit_keeps_history_and_detects_conflict(self):
        doc = self.make_doc(self.alice)
        section = doc.sections.first()
        url = reverse("deliberation:section_edit", args=[section.pk])

        self.client.force_login(self.alice)
        self.client.post(url, {"body": "First version", "note": "", "base_version": 0})
        section.refresh_from_db()
        self.assertEqual(section.version, 1)
        self.assertEqual(section.revisions.count(), 1)

        self.client.force_login(self.bob)
        response = self.client.post(url, {"body": "Stale edit", "note": "", "base_version": 0})
        self.assertContains(response, "saved this section while you were editing")
        section.refresh_from_db()
        self.assertEqual(section.body, "First version")

    def test_replies_stay_one_level_deep(self):
        doc = self.make_doc(self.alice)
        top = Comment.objects.create(document=doc, author=self.alice, body="Top")
        self.client.force_login(self.bob)
        url = reverse("deliberation:comment", args=[doc.pk])
        self.client.post(url, {"kind": "question", "body": "Reply", "parent": top.pk})
        reply = Comment.objects.get(body="Reply")
        self.assertEqual(reply.parent, top)
        self.client.post(url, {"kind": "support", "body": "Reply to reply", "parent": reply.pk})
        self.assertEqual(Comment.objects.get(body="Reply to reply").parent, top)

    def test_people_involved_are_notified_without_revealing_anonymous_authors(self):
        doc = self.make_doc(self.bob)
        self.client.force_login(self.alice)
        self.client.post(reverse("deliberation:comment", args=[doc.pk]), {"kind": "concern", "body": "Risky", "anonymous": "on"})
        note = self.bob.notifications.get()
        self.assertIn("A colleague", note.message)
        self.assertNotIn("Alice", note.message)
        self.assertFalse(self.alice.notifications.exists())     # no notification for your own action
        self.client.force_login(self.bob)
        response = self.client.get(reverse("notifications:open", args=[note.pk]))
        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertIsNotNone(note.read_at)

    def test_anonymous_comment_hides_name(self):
        doc = self.make_doc(self.bob)
        Comment.objects.create(document=doc, author=self.alice, body="Honest concern", kind="concern", anonymous=True)
        self.client.force_login(self.bob)
        response = self.client.get(doc.get_absolute_url())
        self.assertContains(response, "A colleague")
        self.assertNotContains(response, "Alice Rahman")

    def test_only_author_changes_status(self):
        doc = self.make_doc(self.alice)
        url = reverse("deliberation:status", args=[doc.pk])
        self.client.force_login(self.bob)
        self.client.post(url, {"status": "adopted"})
        doc.refresh_from_db()
        self.assertEqual(doc.status, "open")
        self.client.force_login(self.alice)
        self.client.post(url, {"status": "submitted"})
        doc.refresh_from_db()
        self.assertEqual(doc.status, "submitted")
