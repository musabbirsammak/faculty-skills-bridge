# Contributing

Faculty Skills Bridge is built by and for universities. Contributions of code, catalogue data and translations are welcome.

## Principles every change must keep
1. **Skill profiles are private.** No view, export or API may show an individual teacher's skills, suggestions or feedback to anyone else, whatever their role.
2. **Totals, not individuals.** Aggregates must respect `PRIVACY_MIN_GROUP`.
3. **Explainable matching.** A teacher should be able to understand why a course was suggested.

Pull requests that weaken these will not be merged.

## Contributing catalogue data
The shared catalogue lives in `catalog/data/*.json`. To add a discipline, create a new file (see `seed_business.json`) and reference existing skills by name where they fit.

For each course:
- `area` must be an ISCED-F 2013 detailed field code (see `catalog/choices.py`).
- `impact` (1–5) needs an `impact_note` and a `source`. Prefer published sources (e.g. WEF Future of Jobs, national labour-market reports). Otherwise write "Starter rating; review locally".
- Mark the essential skills as `core`.

Say in the pull request which university or colleagues reviewed the data.

## Contributing code
```bash
python manage.py test                       # full suite
python -m unittest catalog.test_matching    # matching logic only
```

- Keep code small and readable. Prefer Django's built-in features to new dependencies.
- **Migrations are part of the repository.** After changing a model, run `python manage.py makemigrations` and commit the new migration files with your change. Never edit a migration that has already been released.
- New pages must work without JavaScript and in both light and dark mode.

## Licence
By contributing you agree that your contribution is licensed under the GNU Affero General Public License v3.0 or later, like the rest of the project.
