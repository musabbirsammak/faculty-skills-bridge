"""Demo data for trying the app or taking screenshots. Every demo account starts with 'demo_'.

    python manage.py seed_demo            # demo faculties, 15 teachers, a head, a dean, a VC, feedback and two documents
    python manage.py seed_demo --remove   # delete everything demo accounts created
"""
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Department, Faculty
from catalog.models import Course, CourseStatusChange, Feedback, Skill, TeacherSkill
from catalog.services import suggestions_for
from deliberation.models import Comment, Document, Revision, Stance

PROFILES = [
    ("Software testing", {"Software testing": "teach", "Test automation": "teach", "Java programming": "teach",
                          "Requirements engineering": "use", "Agile / Scrum": "use", "Python programming": "use", "CI/CD pipelines": "fam"}),
    ("Networking", {"Computer networks": "teach", "Network security": "teach", "Linux administration": "teach",
                    "Operating systems": "use", "Cybersecurity fundamentals": "use", "Cloud computing": "fam", "Python programming": "fam"}),
    ("Databases", {"Relational databases": "teach", "SQL": "teach", "Database design & normalisation": "teach",
                   "NoSQL databases": "use", "Python programming": "use", "Information systems": "use", "Data warehousing & ETL": "fam"}),
    ("Numerical methods", {"Numerical methods": "teach", "Calculus": "teach", "Linear algebra": "teach",
                           "Probability": "use", "Python programming": "use", "Optimisation": "use", "Statistical inference": "fam"}),
    ("Web development", {"Frontend web development": "teach", "Backend & API development": "teach", "JavaScript / TypeScript": "teach",
                         "SQL": "use", "Version control (Git)": "use", "Python programming": "fam"}),
    ("Statistics", {"Probability": "teach", "Statistical inference": "teach", "Regression modelling": "teach", "R programming": "use",
                    "Python programming": "use", "Experimental design & A/B testing": "fam", "Research methods": "use"}),
    ("Operating systems", {"Operating systems": "teach", "C/C++ programming": "teach", "Computer architecture": "teach",
                           "Linux administration": "use", "Embedded systems & IoT": "fam"}),
    ("Project management", {"Software project management": "teach", "Agile / Scrum": "teach", "Team leadership": "use",
                            "Technical writing & communication": "use", "Requirements engineering": "use", "Business analysis": "fam"}),
    ("Security", {"Cybersecurity fundamentals": "teach", "Cryptography": "teach", "Network security": "use",
                  "Penetration testing": "use", "Secure software development": "fam", "Computer networks": "use"}),
    ("Machine learning", {"Machine learning": "teach", "Python programming": "teach", "Deep learning": "use", "Linear algebra": "use",
                          "Model evaluation & validation": "teach", "Probability": "use"}),
    ("Information systems", {"Information systems": "teach", "Business analysis": "teach", "Relational databases": "use",
                             "SQL": "use", "Data visualisation": "fam"}),
    ("HCI", {"HCI & UX design": "teach", "User research": "teach", "Frontend web development": "use",
             "Accessibility": "use", "Participatory design": "fam"}),
    ("Accounting", {"Financial accounting": "teach", "Managerial accounting": "teach", "Auditing": "teach",
                    "Taxation": "use", "Spreadsheet modelling": "teach", "Statistical inference": "fam"}),
    ("Marketing", {"Marketing management": "teach", "Consumer behaviour": "teach", "Market research": "use",
                   "Business communication": "use", "Digital marketing": "fam", "Data visualisation": "fam"}),
    ("Management", {"Strategic management": "teach", "Organisational behaviour": "teach", "Human resource management": "use",
                    "Team leadership": "use", "Change management": "fam", "Business communication": "teach"}),
]
BUSINESS_PROFILES = {"Accounting", "Marketing", "Management"}

POLICY = {
    "title": "A transition plan for every retired course",
    "summary": "When the department removes a course, the teachers who taught it should get a planned path to new "
               "teaching, not a gap in their routine. This proposes a simple protocol the curriculum committee can follow.",
    "sections": {
        "Problem": "Over the last three years several courses were removed as outdated. The decisions were reasonable, "
                   "but nothing was planned for the colleagues who had specialised in them for years. Some now teach "
                   "outside their strengths; others have fewer sections.\n\nStudents lose too: experienced teachers are "
                   "not used where they could help most.",
        "Proposal": "Whenever a course is removed or merged, the curriculum committee prepares a short transition plan "
                    "for each affected teacher, agreed with that teacher, before the change takes effect.\n\nThe plan "
                    "names one or two target courses, the skills to build, a co-teaching semester and the support "
                    "offered (time, training budget, mentoring).",
        "Who is affected": "Teachers of removed courses gain a clear path. Teachers of new courses gain co-teachers. "
                           "The committee takes on one more step per change. Students get experienced teachers in new subjects.",
    },
    "comments": [
        ("Proposal", "support", "This would have helped me two years ago. Agreeing the plan with the teacher is the key part."),
        ("Proposal", "concern", "Who pays for the training? Without a budget line this stays on paper.", True),
        ("How it would work", "suggestion", "Use the Skills Bridge suggestions as the starting point for each plan, so the committee does not start from zero."),
        (None, "question", "Should this also apply when a course is heavily redesigned, not only removed?"),
    ],
    "stances": ["support"] * 6 + ["amend"] * 3 + ["oppose"],
}

# Demo course decisions: (title, status, department short name)
STATUSES = [
    ("Introduction to Programming with Python", "offered", "SWE"), ("Database Systems", "offered", "SWE"),
    ("Machine Learning", "offered", "SWE"), ("Web Application Development", "offered", "CSE"),
    ("Computer Networks", "offered", "CSE"), ("Probability & Statistics", "offered", "SWE"),
    ("Financial Accounting", "offered", "BBA"), ("Principles of Marketing", "offered", "BBA"),
    ("Testing & Red-Teaming AI Systems", "planned", "SWE"), ("MLOps & ML Engineering", "planned", "SWE"),
    ("Business Analytics", "planned", "BBA"),
    ("Software Testing & Quality Assurance", "retiring", "SWE"), ("Numerical Methods", "retiring", "CSE"),
    ("Green & Sustainable Computing", "suggested", None),
]

REDESIGN = {
    "course": "Software Testing & Quality Assurance",
    "title": "Software Testing for the AI era",
    "summary": "Students now generate test cases with AI tools. The course should teach them to judge those tests, "
               "and to test AI-based software itself.",
    "sections": {
        "Why redesign": "AI assistants write unit tests in seconds, often with weak assertions. Industry now needs testers "
                        "who can evaluate AI output and test systems that include machine learning models.",
        "Learning outcomes": "By the end, students can:\n- design tests from requirements without AI help\n- critique "
                             "AI-generated tests and improve them\n- evaluate a model-based feature for robustness and bias",
        "AI use policy": "AI tools are allowed for generating draft tests. Students must submit the prompt, the raw output "
                         "and a short critique of what they kept, changed or rejected.",
    },
    "comments": [
        ("Assessment", "suggestion", "Add a lab where students receive deliberately flawed AI-generated tests and must find the problems."),
        ("Learning outcomes", "support", "Keeping 'without AI help' in the first outcome matters. They need the foundation first."),
        ("AI use policy", "question", "How do we check that the critique is their own work?"),
    ],
}


class Command(BaseCommand):
    help = "Create (or with --remove, delete) demo teachers, feedback and discussions."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true")
        parser.add_argument("--password", default="demo-pass-2027")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        demo_users = User.objects.filter(username__startswith="demo_")
        if options["remove"]:
            Document.objects.filter(created_by__in=demo_users).delete()
            count = demo_users.count()
            demo_users.delete()
            Course.objects.filter(department__faculty__name__endswith="(demo)").update(status=Course.Status.CATALOGUE, department=None)
            Course.objects.filter(title__in=[t for t, s, u in STATUSES if u is None]).update(status=Course.Status.CATALOGUE)
            Department.objects.filter(faculty__name__endswith="(demo)").delete()
            Faculty.objects.filter(name__endswith="(demo)").delete()
            self.stdout.write(self.style.SUCCESS(f"Removed {count} demo accounts and their content."))
            return
        if not Skill.objects.exists():
            raise CommandError("Run `python manage.py seed_catalog` first.")
        needed = {name for _, profile in PROFILES for name in profile}
        missing = needed - set(Skill.objects.filter(name__in=needed).values_list("name", flat=True))
        if missing:
            raise CommandError("Load the business data first: "
                               "python manage.py seed_catalog --file catalog/data/seed_business.json")
        if demo_users.exists():
            raise CommandError("Demo data already exists. Run with --remove first to recreate it.")

        rng = random.Random(2027)
        fsit, _ = Faculty.objects.get_or_create(name="Faculty of Science & Information Technology (demo)", defaults={"short_name": "FSIT"})
        fbe, _ = Faculty.objects.get_or_create(name="Faculty of Business & Entrepreneurship (demo)", defaults={"short_name": "FBE"})
        swe, _ = Department.objects.get_or_create(faculty=fsit, name="Software Engineering", defaults={"short_name": "SWE"})
        cse, _ = Department.objects.get_or_create(faculty=fsit, name="Computer Science & Engineering", defaults={"short_name": "CSE"})
        bba, _ = Department.objects.get_or_create(faculty=fbe, name="Business Administration", defaults={"short_name": "BBA"})

        skills = {s.name: s for s in Skill.objects.all()}
        users = []
        for i, (label, profile) in enumerate(PROFILES, start=1):
            business = label in BUSINESS_PROFILES
            user = User.objects.create_user(
                username=f"demo_{i:02d}", password=options["password"], display_name=f"Demo teacher {i:02d}",
                department=bba if business else (swe if i <= 6 else cse),
                designation=f"Lecturer · {label}",
                field="business" if business else "ict",
            )
            TeacherSkill.objects.bulk_create(TeacherSkill(teacher=user, skill=skills[n], level=lvl) for n, lvl in profile.items())
            users.append(user)

        for user in users:
            cards, _ = suggestions_for(user)
            for card in cards[:6]:
                choice = rng.choices(["fit", "interested", "nofit"], weights=[5, 3, 2])[0]
                Feedback.objects.create(teacher=user, course=card["course"], response=choice)

        leaders = [
            ("demo_head", "Demo head of SWE", swe, User.Role.HEAD),
            ("demo_dean", "Demo dean of FSIT", swe, User.Role.DEAN),
            ("demo_vc", "Demo vice-chancellor", None, User.Role.LEADERSHIP),
        ]
        for username, name, department, role in leaders:
            User.objects.create_user(username=username, password=options["password"], display_name=name,
                                     department=department, role=role)

        vc = User.objects.get(username="demo_vc")
        units = {"SWE": swe, "CSE": cse, "BBA": bba, None: None}
        for title, status, unit in STATUSES:
            course = Course.objects.filter(title=title).first()
            if course:
                CourseStatusChange.objects.create(course=course, old_status=course.status, new_status=status,
                                                  department=units[unit], changed_by=vc, note="Demo decision")
                course.status, course.department = status, units[unit]
                course.save(update_fields=["status", "department", "updated"])

        self._document(Document.Kind.POLICY, POLICY, users[7], users, rng)
        self._document(Document.Kind.REDESIGN, REDESIGN, users[0], users, rng,
                       course=Course.objects.filter(title=REDESIGN["course"]).first(), department=swe)
        self.stdout.write(self.style.SUCCESS(
            f"Created 2 demo faculties, {len(users)} teachers (demo_01 to demo_{len(users):02d}), "
            f"and demo_head, demo_dean, demo_vc. Password: '{options['password']}'."
        ))

    def _document(self, kind, spec, author, users, rng, course=None, department=None):
        doc = Document.objects.create(kind=kind, title=spec["title"], summary=spec["summary"], course=course,
                                      department=department, created_by=author)
        doc.create_sections()
        sections = {s.title: s for s in doc.sections.all()}
        for title, body in spec["sections"].items():
            section = sections[title]
            section.body, section.version, section.updated_by = body, 1, author
            section.save()
            Revision.objects.create(section=section, body=body, author=author, note="First draft")
        others = [u for u in users if u != author]
        for entry in spec["comments"]:
            title, ckind, text = entry[:3]
            anonymous = len(entry) > 3 and entry[3]
            Comment.objects.create(document=doc, section=sections.get(title) if title else None,
                                   author=rng.choice(others), kind=ckind, body=text, anonymous=anonymous)
        for user, value in zip(others, spec.get("stances", [])):
            Stance.objects.create(document=doc, user=user, value=value)
