"""Tests for the matching logic. Plain unittest: runs with or without Django.

    python -m unittest catalog.test_matching      # no database needed
    python manage.py test                         # runs with the rest of the suite
"""
import unittest

from catalog.matching import CourseInput, Requirement, evaluate, explore, learning_priorities, suggest

TEST, AUTO, JAVA, CICD, EVAL, LLM, ML, PY = range(1, 9)
RELATED = {EVAL: {ML, TEST}, TEST: {AUTO, EVAL}, ML: {EVAL}}


def course(cid, core, sup=(), impact=3, emerging=False):
    reqs = [Requirement(s, True) for s in core] + [Requirement(s, False) for s in sup]
    return CourseInput(cid, impact, emerging, reqs)


class EvaluateTests(unittest.TestCase):
    def test_full_coverage_is_ready(self):
        m = evaluate(course(1, [TEST, AUTO], [JAVA]), {TEST: "teach", AUTO: "teach", JAVA: "teach"}, RELATED)
        self.assertEqual(m.percent, 100)
        self.assertEqual(m.tier, "ready")
        self.assertEqual(m.prep_label, "ready now")

    def test_weighted_score(self):
        # core TEST teach (3 x 1.0) + core AUTO familiar (3 x 0.35) + support JAVA missing (1 x 0) = 4.05 / 7
        m = evaluate(course(1, [TEST, AUTO], [JAVA]), {TEST: "teach", AUTO: "fam"}, {})
        self.assertAlmostEqual(m.score, 4.05 / 7)
        self.assertEqual(m.tier, "short")

    def test_high_score_with_weak_core_is_not_ready(self):
        # 3 strong supporting skills cannot hide a missing core skill
        m = evaluate(course(1, [LLM], [TEST, AUTO, JAVA, CICD, PY]),
                     {TEST: "teach", AUTO: "teach", JAVA: "teach", CICD: "teach", PY: "teach"}, {})
        self.assertGreaterEqual(m.score, 0.45)
        self.assertNotEqual(m.tier, "ready")

    def test_related_skill_gives_partial_credit(self):
        m = evaluate(course(1, [EVAL]), {TEST: "teach"}, RELATED)
        self.assertAlmostEqual(m.score, 0.35)
        self.assertEqual(m.head_start[0].via, TEST)
        self.assertEqual(m.tier, "stretch")

    def test_own_skill_beats_related(self):
        m = evaluate(course(1, [EVAL]), {EVAL: "use", TEST: "teach"}, RELATED)
        self.assertAlmostEqual(m.score, 0.7)
        self.assertIsNone(m.items[0].via)

    def test_no_overlap_has_no_tier(self):
        m = evaluate(course(1, [LLM, ML]), {JAVA: "teach"}, RELATED)
        self.assertIsNone(m.tier)
        self.assertEqual(len(m.gaps), 2)

    def test_gaps_list_core_first(self):
        m = evaluate(course(1, [LLM], [PY]), {}, {})
        self.assertTrue(m.gaps[0].core)


class SuggestTests(unittest.TestCase):
    def setUp(self):
        self.courses = [
            course(1, [TEST, AUTO], [JAVA], impact=3),
            course(2, [EVAL, TEST], [LLM, AUTO], impact=5, emerging=True),
            course(3, [LLM, ML], impact=5, emerging=True),
            course(4, [TEST], [JAVA], impact=2),
            course(5, [], impact=5),
        ]
        self.levels = {TEST: "teach", AUTO: "teach", JAVA: "teach"}

    def test_order_is_tier_then_impact(self):
        ids = [m.course.id for m in suggest(self.courses, self.levels, RELATED)]
        self.assertEqual(ids[:2], [1, 4])  # both ready: impact 3 before impact 2
        self.assertIn(2, ids)
        self.assertNotIn(3, ids)  # no overlap
        self.assertNotIn(5, ids)  # course without skills is skipped

    def test_emerging_only(self):
        ids = [m.course.id for m in suggest(self.courses, self.levels, RELATED, emerging_only=True)]
        self.assertEqual(ids, [2])

    def test_explore_keeps_far_courses_closest_first(self):
        matches = explore(self.courses, self.levels, RELATED)
        ids = [m.course.id for m in matches]
        self.assertIn(3, ids)        # no overlap, but still shown
        self.assertNotIn(5, ids)     # course without skills
        self.assertEqual(ids[-1], 3)
        far = learning_priorities(matches, tiers=("short", "stretch", None))
        self.assertIn(LLM, [s for s, _, _ in far])

    def test_learning_priorities_point_at_missing_skills(self):
        matches = suggest(self.courses, self.levels, RELATED)
        top = learning_priorities(matches)
        self.assertEqual(top[0][0], EVAL)  # core, high-impact gap
        self.assertIn(2, top[0][2])


if __name__ == "__main__":
    unittest.main()
