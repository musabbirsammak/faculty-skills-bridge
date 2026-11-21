# Faculty Skills Bridge

Open-source software that helps a university and its teachers through AI-era curriculum change.

Teachers add their skills and see which courses they could teach now, after a short preparation, or as a stretch, with recent high-impact subjects first and the skills to learn next. The university gets two shared spaces to work the change out together, **policy proposals** and a **course redesign studio**, plus totals-only **insights** for heads, deans and leadership.

Each university runs its own copy on its own domain. The starter catalogue covers computing and business; any discipline can be added.

Python, Django and MySQL. No JavaScript framework and no build step. Licensed under AGPL-3.0.

## Features

**Accounts and roles**
- Teachers register with their university email (allowed domains are set by the university), optionally subject to approval by an administrator, and pick their department.
- Roles: *Teacher*, *Head of department*, *Dean*, *University leadership*. Roles change which totals someone sees, never access to individuals.
- The university's name and logo appear under the product name. Password reset by email.

**Skills to course paths**
- Search and add skills (aliases included, so "docker" finds Containers), each with a level: *can teach it*, *use it regularly*, *familiar*.
- Suggestions in three tiers, ordered by impact, showing the skills you bring, the ones you have a head start on, the ones to learn, a suggested path and the preparation time.
- *Skills that open the most doors*: the missing skills that bring the most high-impact courses within reach.
- Works across disciplines: courses are classified by UNESCO ISCED-F 2013 detailed field, and paths outside a teacher's own field are marked.
- Feedback on each suggestion ("Makes sense", "Doesn't fit", "Interested").
- A living catalogue: teachers suggest courses and skills, vote on suggestions, and propose changes that responsible heads, deans or leaders accept or decline.
- Course status per university (suggested, planned, offered, retiring), decided by heads, deans and leadership, with a history.

**Insights** (totals only)
- University, faculty and department views: participation, shared training needs, recent subjects nobody is ready to teach, a breakdown by unit, and the status of proposals and redesigns.
- Teachers see their university and department; deans also see their faculty and its departments; leadership sees every unit.
- Any number below `PRIVACY_MIN_GROUP` (default 3) is hidden.

**Notifications**
- A bell with unread count: people are notified when something they are involved in changes (comments, edits, stages, status decisions, proposed changes, votes). Optional email.

**Policy proposals and course redesign studio**
- Documents with guiding sections that anyone can edit. Every save is kept, with a line-by-line history and protection against overwriting someone else's edit.
- Comments tagged as suggestion, support, concern or question; replies; anonymous posting; stances shown as totals.
- Each document can belong to a department or to the whole university, and moves through stages from drafting to adopted.

## Privacy by design
A teacher's skills, suggestions and feedback are visible only to that teacher. No role, including leadership, can open an individual profile. The in-app page *What can others see?* explains this to every user. See [CONTRIBUTING.md](CONTRIBUTING.md) for the rules every change must keep.

## Try it on your computer

Requirements: Python 3.10–3.13 and MySQL 8 (or use SQLite for a quick look).

```bash
git clone <repository-url> faculty-skills-bridge
cd faculty-skills-bridge
python3 -m venv .venv && source .venv/bin/activate      # or a conda environment with Python 3.12
pip install -r requirements.txt
cp .env.example .env                                     # set DB_ENGINE=sqlite to skip MySQL
python manage.py migrate
python manage.py seed_catalog
python manage.py seed_catalog --file catalog/data/seed_business.json
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000, then set up your institution, faculties and departments at http://127.0.0.1:8000/admin.

`mysqlclient` needs MySQL client headers: on macOS `brew install mysql pkg-config` and `export PKG_CONFIG_PATH="$(brew --prefix)/opt/mysql/lib/pkgconfig"`; on Ubuntu `sudo apt install python3-dev default-libmysqlclient-dev build-essential pkg-config`.

Demo data (15 teachers in two faculties, plus a demo head, dean and VC):
```bash
python manage.py seed_demo            # passwords: demo-pass-2027
python manage.py seed_demo --remove
```

Tests:
```bash
python manage.py test
python -m unittest catalog.test_matching   # matching logic only, no database
```

## Install it for your university
See [docs/INSTALL.md](docs/INSTALL.md): Docker, automatic HTTPS, backups and a privacy checklist.

## Handbook
Open [docs/handbook.html](docs/handbook.html) in a browser: a complete user manual covering roles, every page, the calculations with a worked example, impact ratings, best practices and next steps.

## How it works
See [docs/METHODOLOGY.md](docs/METHODOLOGY.md): the matching method, how the starter catalogue and impact ratings were made, the ISCED-F classification, and the known limits.

More skills can be imported from the EU's ESCO classification:
```bash
python manage.py import_esco path/to/digitalSkillsCollection_en.csv --family prog
```

## Project layout
```
config/          settings, URLs, home and privacy pages
accounts/        users, roles, institution, faculties and departments
catalog/         skills, courses, matching, suggestions, insights
  matching.py    the matching method (framework-free)
  scopes.py      which totals each role may see
  choices.py     ISCED-F fields of education
  data/          starter catalogues (JSON)
  management/    seed_catalog, seed_demo, import_esco
deliberation/    policy proposals and the course redesign studio
notifications/   in-app (and optional email) notifications
templates/, static/
docs/            installation guide and methodology
```

## Contributing
Universities can improve the code and the shared catalogue. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence
GNU Affero General Public License v3.0 or later. If you modify the software and run it for others, you must share your changes under the same licence.
