"""Import skills from the EU's ESCO classification.

Download a CSV from https://esco.ec.europa.eu/en/use-esco/download (choose CSV and English).
Good starting files: digitalSkillsCollection_en.csv (digital skills only) or skills_en.csv (all ~13,900 skills).
"""
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Skill


class Command(BaseCommand):
    help = "Import skills from an ESCO CSV file. Existing skills keep their data and gain the ESCO link."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--family", default=Skill.Family.OTHER, choices=Skill.Family.values)
        parser.add_argument("--contains", default="", help="Comma-separated words; import only labels containing one.")
        parser.add_argument("--limit", type=int, default=0)

    @transaction.atomic
    def handle(self, *args, **options):
        words = [w.strip().lower() for w in options["contains"].split(",") if w.strip()]
        created = linked = 0
        try:
            handle = open(options["path"], encoding="utf-8", newline="")
        except OSError as exc:
            raise CommandError(f"Cannot open {options['path']}: {exc}")
        with handle:
            reader = csv.DictReader(handle)
            if not {"preferredLabel", "conceptUri"} <= set(reader.fieldnames or []):
                raise CommandError("This does not look like an ESCO skills CSV (needs preferredLabel and conceptUri).")
            for row in reader:
                label = (row.get("preferredLabel") or "").strip()[:160]
                if not label or (words and not any(w in label.lower() for w in words)):
                    continue
                uri = (row.get("conceptUri") or "").strip()[:255]
                existing = Skill.objects.filter(name__iexact=label).first()
                if existing:
                    if not existing.esco_uri:
                        existing.esco_uri = uri
                        existing.save(update_fields=["esco_uri"])
                        linked += 1
                    continue
                aliases = [a.strip() for a in (row.get("altLabels") or "").splitlines() if a.strip()][:20]
                Skill.objects.create(
                    name=label, family=options["family"], aliases=", ".join(aliases),
                    description=(row.get("description") or "").strip()[:2000], esco_uri=uri,
                )
                created += 1
                if options["limit"] and created >= options["limit"]:
                    break
        self.stdout.write(self.style.SUCCESS(f"Imported {created} new skills; linked {linked} existing skills to ESCO."))
