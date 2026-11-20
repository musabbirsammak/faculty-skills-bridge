"""Skill-to-course matching. Plain Python with no Django imports, so it can be tested on its own.

Method (deliberately simple and explainable):
- A course lists core skills (weight 3) and supporting skills (weight 1).
- A teacher's level gives credit: can teach 1.0, use regularly 0.7, familiar 0.35.
- A closely related skill the teacher has gives up to 0.35 x its level.
- Match = weighted share of the course the teacher already covers.
- Tiers: ready (>= 0.70 and every core skill >= 0.6), short (>= 0.45), stretch (>= 0.25).
"""
from collections import defaultdict
from dataclasses import dataclass, field

LEVEL_CREDIT = {"teach": 1.0, "use": 0.7, "fam": 0.35}
CORE_WEIGHT = 3
SUPPORT_WEIGHT = 1
RELATED_FACTOR = 0.35
STRONG = 0.6
READY, SHORT, STRETCH = 0.70, 0.45, 0.25
TIER_ORDER = ("ready", "short", "stretch")


@dataclass(frozen=True)
class Requirement:
    skill_id: int
    core: bool


@dataclass
class CourseInput:
    id: int
    impact: int
    emerging: bool
    requirements: list


@dataclass
class Item:
    skill_id: int
    core: bool
    weight: int
    credit: float
    own: float
    via: int | None


@dataclass
class Match:
    course: CourseInput
    score: float
    tier: str | None
    items: list = field(default_factory=list)
    prep_load: float = 0.0

    @property
    def percent(self):
        return round(self.score * 100)

    @property
    def have(self):
        return [i for i in self.items if i.own >= STRONG]

    @property
    def head_start(self):
        """Skills partly covered: known at 'familiar' level, or reachable through a related skill."""
        return sorted((i for i in self.items if i.own < STRONG and i.credit > 0), key=lambda i: -i.weight)

    @property
    def gaps(self):
        return sorted((i for i in self.items if i.credit == 0), key=lambda i: -i.weight)

    @property
    def prep_label(self):
        if self.prep_load == 0:
            return "ready now"
        if self.prep_load <= 2.5:
            return "a few weeks"
        if self.prep_load <= 6:
            return "about one semester"
        return "two semesters or more"


def credit_for(skill_id, levels, related):
    """Return (credit, own_credit, via_skill_id) for one required skill."""
    own = LEVEL_CREDIT.get(levels.get(skill_id), 0.0)
    best, via = 0.0, None
    for other in related.get(skill_id, ()):
        value = RELATED_FACTOR * LEVEL_CREDIT.get(levels.get(other), 0.0)
        if value > best:
            best, via = value, other
    if own >= best:
        return own, own, None
    return best, own, via


def evaluate(course, levels, related):
    items, num, den, load = [], 0.0, 0, 0.0
    for req in course.requirements:
        weight = CORE_WEIGHT if req.core else SUPPORT_WEIGHT
        credit, own, via = credit_for(req.skill_id, levels, related)
        items.append(Item(req.skill_id, req.core, weight, credit, own, via))
        num += weight * credit
        den += weight
        if credit < STRONG:
            load += weight * (1 - credit)
    score = num / den if den else 0.0
    core_ok = all(i.credit >= STRONG for i in items if i.core)
    if score >= READY and core_ok:
        tier = "ready"
    elif score >= SHORT:
        tier = "short"
    elif score >= STRETCH:
        tier = "stretch"
    else:
        tier = None
    return Match(course=course, score=score, tier=tier, items=items, prep_load=round(load, 2))


def suggest(courses, levels, related, emerging_only=False):
    """Matches that reach a tier, ordered by tier, then impact (higher first), then match."""
    matches = [evaluate(c, levels, related) for c in courses if c.requirements and (c.emerging or not emerging_only)]
    matches = [m for m in matches if m.tier]
    return sorted(matches, key=lambda m: (TIER_ORDER.index(m.tier), -m.course.impact, -m.score))


def explore(courses, levels, related):
    """Every course with skills, closest first and with no threshold: for exploring a new area."""
    matches = [evaluate(c, levels, related) for c in courses if c.requirements]
    return sorted(matches, key=lambda m: (-m.score, -m.course.impact))


def learning_priorities(matches, limit=5, tiers=("short", "stretch")):
    """Skills worth learning next: missing or partial skills, weighted by how much impact they unlock.

    Only courses in the given tiers count (use None for courses below the stretch threshold).
    Returns a list of (skill_id, value, [course ids]) sorted by value.
    """
    value = defaultdict(float)
    unlocks = defaultdict(list)
    for m in matches:
        if m.tier not in tiers:
            continue
        for item in m.items:
            if item.credit < STRONG:
                value[item.skill_id] += m.course.impact * item.weight * (1 - item.credit)
                unlocks[item.skill_id].append(m.course.id)
    ranked = sorted(value, key=lambda s: (-value[s], s))[:limit]
    return [(s, round(value[s], 2), unlocks[s]) for s in ranked]
