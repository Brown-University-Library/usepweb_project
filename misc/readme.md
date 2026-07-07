##### 'misc' directory notes

- `schema.xml` is used by the us-epigraphy solr instance. It's stored here to track version-changes.


##### DB transfer command

The database export/import workflow from `PLAN__db_export_import_script.md` is implemented as a Django management
command:

```bash
uv run ./manage.py db_transfer_validation --help
uv run ./manage.py db_transfer_validation inspect-drift --database default
uv run ./manage.py db_transfer_validation export --database default --output-dir ../db_exports
uv run ./manage.py db_transfer_validation import --input-dir ../db_exports/EXPORT_DIR --sqlite-path /path/to/new.sqlite3
uv run ./manage.py db_transfer_validation validate --input-dir ../db_exports/EXPORT_DIR --sqlite-path /path/to/new.sqlite3
```

Exports default to `../db_exports` from the project root and include:

- `manifest.json`
- `fixture.django.json`
- `schema.json`
- `schema-source.sql`
- `checksums.json`
- `data/*.jsonl` only when schema/model drift is detected

The import path creates the SQLite schema through Django (`migrate --run-syncdb`) and loads the Django fixture. It does
not require the external `sqlite3` command-line tool.

---
