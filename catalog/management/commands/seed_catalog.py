import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Course, CourseSkill, Skill

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "seed_catalog.json"


class Command(BaseCommand):
    help = "Load the starter skills and courses. Existing records are kept unless --update is given."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE))
        parser.add_argument("--update", action="store_true", help="Overwrite existing records with the file's values.")

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(Path(options["file"]).read_text(encoding="utf-8"))
        save = Skill.objects.update_or_create if options["update"] else Skill.objects.get_or_create

        for s in data.get("skills", []):
            save(name=s["name"], defaults={"family": s["family"], "aliases": s.get("aliases", ""),
                                           "description": s.get("description", "")})
        # Look skills up across the whole database, so a file can refer to skills loaded by another file.
        skills = {s.name: s for s in Skill.objects.all()}
        for s in data.get("skills", []):
            skills[s["name"]].related.add(*(skills[r] for r in s.get("related", [])))

        save_course = Course.objects.update_or_create if options["update"] else Course.objects.get_or_create
        for c in data.get("courses", []):
            course, created = save_course(title=c["title"], defaults={
                "area": c["area"], "emerging": c["emerging"], "impact": c["impact"],
                "impact_note": c.get("impact_note", ""), "source": c.get("source", ""),
                "description": c.get("description", ""),
            })
            if created or options["update"]:
                for name, core in [(n, True) for n in c["core"]] + [(n, False) for n in c["supporting"]]:
                    CourseSkill.objects.update_or_create(course=course, skill=skills[name], defaults={"core": core})

        self.stdout.write(self.style.SUCCESS(
            f"Catalogue ready: {Skill.objects.count()} skills, {Course.objects.count()} courses."
        ))
