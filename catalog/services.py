"""Bridges between the database and the framework-free matching module."""
from collections import defaultdict

from .matching import CourseInput, Requirement, explore, learning_priorities, suggest
from .models import Course, CourseSkill, Skill, TeacherSkill

STEP_TEXT = {
    "ready": [
        "Offer to teach a section next semester.",
        "{learn_short}",
    ],
    "short": [
        "Study {learn} with a MOOC, textbook or short course.",
        "Co-teach one semester with a colleague who already teaches it.",
        "Lead your own section the following semester.",
    ],
    "stretch": [
        "Build a small project that uses {learn_two}.",
        "Sit in on the course for a semester, then co-teach it.",
        "Plan on about a year before teaching it alone.",
    ],
    "far": [
        "Start with an introductory course in {learn_two}.",
        "Sit in on the course for a semester to see what teaching it involves.",
        "Plan on more than a year, with a semester of co-teaching before teaching it alone.",
    ],
}


def load_catalog(field=""):
    """Course inputs (optionally for one field of study) and the related-skill graph."""
    course_rows = Course.objects.all()
    links = CourseSkill.objects.all()
    if field:
        course_rows = course_rows.filter(field=field)
        links = links.filter(course__field=field)
    reqs = defaultdict(list)
    for course_id, skill_id, core in links.values_list("course_id", "skill_id", "core"):
        reqs[course_id].append(Requirement(skill_id, core))
    courses = [
        CourseInput(c["id"], c["impact"], c["emerging"], reqs.get(c["id"], []))
        for c in course_rows.values("id", "impact", "emerging")
    ]
    related = defaultdict(set)
    for a, b in Skill.related.through.objects.values_list("from_skill_id", "to_skill_id"):
        related[a].add(b)
    return courses, related


def levels_for(user):
    return dict(TeacherSkill.objects.filter(teacher=user).values_list("skill_id", "level"))


def _names(skills):
    names = [s.name for s in skills]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def present(matches):
    """Turn matches into template-friendly dicts with Course and Skill objects attached."""
    course_map = Course.objects.in_bulk([m.course.id for m in matches])
    skill_ids = {i.skill_id for m in matches for i in m.items} | {i.via for m in matches for i in m.items if i.via}
    skill_map = Skill.objects.in_bulk(skill_ids)
    cards = []
    for m in matches:
        to_learn = [skill_map[i.skill_id] for i in m.gaps + m.head_start]
        fill = {
            "learn": _names(to_learn[:3]),
            "learn_two": _names(to_learn[:2]),
            "learn_short": f"Brush up on {_names(to_learn[:2])} before you start."
            if to_learn else "Compare your plan with a recent syllabus from another university.",
        }
        cards.append({
            "match": m,
            "course": course_map[m.course.id],
            "have": [(skill_map[i.skill_id], i) for i in m.have],
            "head_start": [(skill_map[i.skill_id], i, skill_map.get(i.via)) for i in m.head_start],
            "gaps": [(skill_map[i.skill_id], i) for i in m.gaps],
            "tier": m.tier or "far",
            "steps": [s.format(**fill) for s in STEP_TEXT[m.tier or "far"]],
        })
    return cards


def suggestions_for(user, emerging_only=False, field=""):
    courses, related = load_catalog(field)
    matches = suggest(courses, levels_for(user), related, emerging_only=emerging_only)
    return present(matches), _priority_rows(learning_priorities(matches))


def _priority_rows(priorities):
    skill_map = Skill.objects.in_bulk([p[0] for p in priorities])
    course_map = Course.objects.in_bulk({cid for p in priorities for cid in p[2]})
    return [{"skill": skill_map[s], "value": v, "courses": [course_map[c] for c in cids]} for s, v, cids in priorities]


def explore_for(user, field):
    """Every course in one field of study, closest first, with what to learn for each."""
    courses, related = load_catalog(field)
    matches = explore(courses, levels_for(user), related)
    priorities = learning_priorities(matches, tiers=("short", "stretch", None))
    return present(matches), _priority_rows(priorities)
