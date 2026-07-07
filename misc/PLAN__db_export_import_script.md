# Plan: Portable DB Export/Import Script

## Goal

Create a Python-based Django-aware export/import script that can:

1. Export the live database schema as observed from the database itself.
2. Export all essential data needed to recreate/repopulate a clean database, including Django admin users/superusers.
3. Create and populate a new SQLite database from the export without requiring a modern external `sqlite3` CLI.
4. Produce artifacts useful for either SQLite or MySQL targets.

The key constraint is that the live database may be slightly out of sync with the current Django models/migrations, so the live database must be treated as the source of truth for schema capture.

## Table Of Contents

- [Goal](#goal)
- [Repository Directives To Follow](#repository-directives-to-follow)
- [Current Project Observations](#current-project-observations)
- [Recommended Shape](#recommended-shape)
- [First-Version Mental Model](#first-version-mental-model)
- [Export Artifact Design](#export-artifact-design)
- [Command Interface](#command-interface)
- [Django-Managed SQLite Import Strategy](#django-managed-sqlite-import-strategy)
- [Raw Export Fallback Strategy](#raw-export-fallback-strategy)
- [Data Scope Defaults](#data-scope-defaults)
- [Implementation Phases](#implementation-phases)
- [Testing Plan](#testing-plan)
- [Resolved Decisions](#resolved-decisions)
- [Recommended First Implementation Decision](#recommended-first-implementation-decision)
- [Prompts](#prompts)

## Repository Directives To Follow

From `usepweb_project/AGENTS.md`:

- Run code with `uv`, not bare `python`.
- Run scripts as `uv run ./path_to_script.py --help`.
- Run Django management commands as `uv run ./manage.py THE-COMMAND`.
- Use the Python version specified in `pyproject.toml`: `>=3.8,<3.9`.
- Write type hints in a Python 3.8-compatible style. Avoid PEP 604 unions such as `str | None`.
- Avoid unguarded Python 3.9+ builtin generics such as `list[str]` unless the implementation explicitly uses
  `from __future__ import annotations`; the simpler default should be `typing.List`, `typing.Dict`, and `typing.Optional`
  where needed.
- Runnable modules should use `def main() -> None` plus `if __name__ == '__main__': main()`.
- Keep `main()` simple; put real logic in top-level helper functions.
- Prefer single-return functions and explicit control flow.
- Use docstrings in the repository's expected format if implementation adds non-test functions.
- Inspect `ruff.toml`; current project formatting uses single quotes, line length 125, 4-space indentation.
- New behavior should usually have focused tests.

Note: `AGENTS.md` mentions Python 3.12 as an ideal target, but this plan intentionally follows `pyproject.toml`
because it is the active project metadata for dependency resolution and runtime compatibility.

## Current Project Observations

- Django settings are in `config/settings.py`.
- `DATABASES` is loaded entirely from `USEPWEB__DATABASES_JSON`.
- Installed Django apps include the standard admin/auth/contenttypes/sessions stack and `usep_app`.
- `usep_app` has model-backed tables for:
  - `FlatCollection`
  - `AboutPage`
  - `TextsPage`
  - `LinksPage`
  - `ContactsPage`
  - `PublicationsPage`
- No `migrations/` directory was found under `usep_app`.
- `misc/` already exists and currently contains Solr-related schema notes.

## Recommended Shape

Implement this as a Django management command, not a standalone script.

Proposed path:

```text
usepweb_project/usep_app/management/commands/db_transfer_validation.py
```

Why:

- It automatically gets Django settings, app registry, database connections, serializers, and auth models.
- It can use Django's database introspection APIs while still issuing backend-specific SQL when needed.
- It can be run consistently with:

```bash
uv run ./manage.py db_transfer_validation --help
```

Optional later convenience wrapper:

```text
usepweb_project/misc/db_transfer_validation.py
```

That wrapper should only call the management command if there is a strong reason to support script-style invocation.

## First-Version Mental Model

The first implementation should be fixture-centered, not a full MySQL-to-SQLite schema/data converter.

Django fixtures are the primary portability mechanism:

1. `inspect-drift`: report whether the live database appears safe to move through Django models/fixtures.
2. `export`: create a Django fixture for model-compatible data, plus schema/drift reports as safety artifacts.
3. `import`: create a Django-managed SQLite database, run Django's schema-creation path, then load the fixture.
4. `validate`: compare source/export/target counts and key records after import.

The raw schema and row exports are audit/fallback artifacts. They help detect drift and preserve evidence of the live
database, but the first version should not attempt to rebuild SQLite directly from MySQL DDL or raw row JSON.

## Export Artifact Design

Create an export directory containing multiple files rather than one huge file. Exports should be written outside the
Git-committed Django project directory, in the outer `usep_webapp_stuff/db_exports/` directory. The command should
auto-create this directory if it does not already exist.

Suggested directory name:

```text
../db_exports/YYYYMMDD_HHMMSS__source-alias/
```

Suggested files:

```text
manifest.json
fixture.django.json
schema.json
schema-source.sql
data/
  table-name.jsonl
checksums.json
import-report.json
```

For the first implementation, `fixture.django.json`, `manifest.json`, `schema.json`, and `schema-source.sql` are the core
export artifacts. The `data/table-name.jsonl` files should be generated only when the drift report shows drift, so the
live rows can be manually inspected. They are useful as a raw audit/fallback export, but should not be required for the
standard `import` path.

### `manifest.json`

Purpose: make the export self-describing and auditable.

Include:

- export timestamp
- project name
- Django version
- Python version
- database engine/vendor
- source database alias
- source database name, with password/host secrets omitted or redacted
- installed apps
- command options used
- table list
- row counts by table
- excluded tables, if any
- export format version

### `schema.json`

Purpose: capture live database structure for drift inspection, validation, and audit.

Use Django connection introspection where possible:

- table names
- table type, if available
- columns
- column database type
- nullability
- default values
- primary key flags
- max lengths, precision, scale where available
- indexes
- unique constraints
- foreign keys
- check constraints where available

Also include a best-effort model comparison section:

- tables Django expects from registered models
- live tables without matching registered models
- registered models whose expected table is absent
- live columns not represented by current models
- model fields not present in live columns

This report is important because the project may have drifted away from model/migration state. It should inform whether
the fixture-centered import is safe; it should not be treated as the normal source for generating SQLite tables in the
first implementation.

### `schema-source.sql`

Purpose: preserve the source database's native Data Definition Language (DDL), meaning the SQL that defines database
structure, for reference and emergency recovery.

For MySQL:

- collect `SHOW CREATE TABLE table_name` for each table

For SQLite:

- collect relevant `sqlite_master` DDL

This file is not the primary cross-backend import format. It is a reference artifact because MySQL DDL cannot be safely replayed directly into SQLite without translation.

### `data/table-name.jsonl`

Purpose: conditional backend-neutral full-table data export for audit and emergency fallback when drift is detected.

Use one JSON object per row:

```json
{"id": 1, "username": "admin", "...": "..."}
```

Benefits:

- Streamable for large tables.
- Independent of Django serializers, so it can include drifted columns and non-model tables.
- Preserves primary keys and admin user password hashes.
- Gives a last-resort data source if the fixture path misses drifted tables/columns.
- Allows manual inspection when the drift report indicates that the database and models are out of sync.

Implementation notes:

- Read rows using database cursors, not ORM model instances.
- Serialize dates, datetimes, decimals, bytes, and JSON-like values predictably.
- Store type hints in `schema.json` so a later fallback importer could coerce values if needed.
- Preserve table names and column names exactly.
- Generate JSONL row exports automatically when the drift report shows drift.
- Do not make JSONL the standard first-version import path.

### `fixture.django.json`

Purpose: create a standard Django fixture for model-compatible data.

Use Django's serializer or call `dumpdata`-equivalent APIs for registered models only.

Include at least:

- `auth.User`
- `auth.Group`
- `auth.Permission`
- `contenttypes.ContentType`
- `usep_app` models

This is the primary first-version import artifact. It is intended to load into a database whose schema has been created by
Django. The schema/drift reports and optional raw row export exist because fixtures can ignore unknown live tables/columns
and may fail if the live database has drifted from current models.

Default first-version behavior should exclude `sessions.Session`; sessions are usually ephemeral, while admin users and
permissions are essential.

### `checksums.json`

Purpose: allow confidence checks after copy/import.

Include:

- row counts by table
- SHA-256 checksum for `fixture.django.json`
- SHA-256 checksum per JSONL file, if drift-triggered raw row export is generated
- optional per-table checksum derived from primary-key-ordered row JSON

## Command Interface

Proposed command:

```bash
uv run ./manage.py db_transfer_validation export --database default --output-dir ../db_exports
uv run ./manage.py db_transfer_validation import --input-dir ../db_exports/EXPORT_DIR --sqlite-path /path/to/new.sqlite3
uv run ./manage.py db_transfer_validation inspect-drift --database default
uv run ./manage.py db_transfer_validation validate --input-dir ../db_exports/EXPORT_DIR --database default
```

First-implementation subcommands:

- `export`: write Django fixture, schema/drift audit artifacts, manifest, and checksums.
- `import`: create a Django-managed SQLite database and load `fixture.django.json`.
- `inspect-drift`: report live-schema/model drift without exporting data.
- `validate`: compare an export against a database or imported SQLite file.

Possible future additional subcommands:

- `export-schema`: write only schema artifacts.
- `export-data`: write only row data artifacts.
- `export-fixture`: write only Django fixture.
- `summarize-export`: print manifest, row counts, and source/target metadata.
- `compare`: compare two export directories or an export directory against a live database.

Important first-implementation options:

- `--database default`
- `--output-dir PATH`, defaulting to `../db_exports` from the project root
- `--input-dir PATH`
- `--sqlite-path PATH`
- `--drop-existing-sqlite`, explicit opt-in to overwrite a target SQLite file
- `--batch-size N`
- `--verbosity`

Possible future additional options:

- `--include-table TABLE`, repeatable
- `--exclude-table TABLE`, repeatable
- `--include-ephemeral`, to include tables such as `django_session`
- `--schema-only`
- `--data-only`
- `--indent-fixture`
- `--dry-run`
- `--force-in-repo-output`, explicit opt-in to write exports inside the Git-committed repo

## Django-Managed SQLite Import Strategy

For `import`, use Django's normal schema and fixture-loading mechanisms. Do not shell out to the SQLite CLI, and do not
translate MySQL schema into SQLite DDL in the first implementation.

Process:

1. Refuse to overwrite an existing SQLite file unless `--drop-existing-sqlite` is passed.
2. Configure the import target as a SQLite Django database connection for the command run.
3. Create the schema through Django:
   - Prefer `migrate` for apps with migrations.
   - Use Django's `migrate --run-syncdb` behavior for apps without migrations, which matters here because `usep_app`
     currently has no `migrations/` directory.
4. Load `fixture.django.json` using Django's fixture loading behavior, equivalent to `loaddata`.
5. Run validation:
   - table list sanity check
   - row counts for model-backed tables
   - admin/superuser presence checks
   - selected primary-key spot checks
   - optional comparison against `manifest.json` and `schema.json`

This keeps the first implementation aligned with Django's intended cross-database portability model.

## Raw Export Fallback Strategy

The script should not initially try to synthesize portable MySQL DDL from SQLite/MySQL schema JSON unless that becomes
necessary.

Use raw artifacts this way:

1. Use `schema.json` and `schema-source.sql` to inspect and document drift.
2. Use `data/table-name.jsonl` as an emergency archive of rows that Django fixtures cannot represent.
3. Treat any direct raw-row import into SQLite as a later enhancement, not the standard first-version `import`.
4. Use `schema-source.sql` only when importing back into the same backend family and after manual review.

The plan should explicitly document that MySQL-to-SQLite DDL conversion and raw JSONL-driven database reconstruction are
out of scope for the first implementation unless requested later.

## Data Scope Defaults

Default fixture export should include model-backed data needed to recreate the application in a Django-managed database.
If the drift report shows drift, raw audit export should include JSONL rows for manual inspection. These tables are not
huge, so the first implementation can favor complete inspectability over table-by-table tuning.

Default fixture exclusions:

- `django_session`; session rows are usually ephemeral

Candidate default fixture inclusions:

- all `auth_*` tables
- all `django_content_type` rows
- all `django_admin_log` rows
- all `usep_app_*` tables

Drift-triggered raw audit inclusions:

- all fixture-included tables
- all other live Django tables except `django_session`
- any unexpected table or column found by the drift report, even though no non-Django MySQL tables are expected

Admin superusers are stored in `auth_user`; preserving full rows preserves password hashes, staff/superuser flags, emails, names, and timestamps.

## Implementation Phases

### Phase 1: Discovery and safety

- Add management command skeleton.
- Add helpers for:
  - resolving output directory, defaulting to the outer `../db_exports` directory
  - creating `../db_exports` if it does not already exist
  - refusing to place export artifacts inside the Git-committed repo unless explicitly overridden
  - opening selected Django database connection
  - listing tables
  - collecting row counts
  - redacting database settings
- Implement `inspect-drift`.
- Write tests for table inclusion/exclusion and manifest generation.

### Phase 2: Schema export

- Implement structured schema introspection using Django APIs.
- Add backend-specific raw DDL capture for MySQL and SQLite.
- Add model-vs-live-schema comparison.
- Write `schema.json`, `schema-source.sql`, and schema sections in `manifest.json`.
- Test against SQLite in Django tests.

### Phase 3: Data export

- Generate `fixture.django.json` for registered models.
- Ensure `auth.User` rows are included, preserving password hashes and superuser flags.
- Decide whether permissions/contenttypes should be full export or natural-key fixture.
- Add row counts and checksums.
- Add default exclusion handling.
- Test that a fixture can be loaded into a Django-created test DB.

### Phase 4: Drift-triggered raw row audit export

- Generate JSONL row exports when the drift report shows drift.
- Use stable primary-key ordering where possible.
- Add type serialization helpers for audit output.
- Keep this output separate from the standard `import` path.
- Test export of tricky values: `None`, empty string, datetime, decimal-like strings, unicode text, booleans, bytes if present.

### Phase 5: Django-managed SQLite import

- Implement target SQLite setup.
- Run Django schema creation through `migrate`, using `run_syncdb` behavior for apps without migrations.
- Load `fixture.django.json` through Django fixture loading.
- Avoid external SQLite CLI.
- Test by exporting from a test DB, importing to a temporary SQLite file, then validating counts/data and superuser presence.

### Phase 6: Documentation

- Add usage notes in `misc/readme.md` or a dedicated doc.
- Include examples for:
  - full export from old MySQL dev-server
  - create SQLite database from export
  - validate imported SQLite database
  - load Django fixture into a Django-created database
  - inspect raw audit artifacts when drift is reported

## Testing Plan

Use Django's test framework through the repository's expected runner if available:

```bash
uv run ./run_tests.py
```

If `run_tests.py` is still absent, use the closest project-supported Django command after confirming with the repository:

```bash
uv run ./manage.py test
```

Focused tests should cover:

- command argument parsing
- manifest redacts credentials
- schema introspection returns expected tables/columns
- Django fixture includes `auth.User` superusers
- SQLite import creates Django-managed tables, loads the fixture, and preserves superusers
- overwrite protection for existing SQLite target
- default exclusion/inclusion rules
- drift-triggered JSONL audit export preserves primary keys and row values

## Resolved Decisions

1. Keep `django_session` out of the first implementation; session rows are ephemeral.
2. Treat `django_admin_log` row data as essential transfer data, and include it in the standard fixture export/import.
3. No live MySQL tables outside the Django-managed tables are expected to require preservation.
4. Scope the first implementation to MySQL source -> SQLite target. Tests may still use SQLite where that is the practical
   local test backend.
5. Generate JSONL row exports when the drift report shows drift, so rows can be manually inspected. Do not use JSONL as the
   standard import path.

## Recommended First Implementation Decision

Build a fixture-centered transfer/validation tool:

- Use `inspect-drift` and schema artifacts to decide whether the fixture path is safe.
- Use `fixture.django.json` as the primary portable data artifact.
- Use Django schema creation plus `loaddata`-equivalent fixture loading to create the SQLite database.
- Use raw schema/row exports only as audit and fallback evidence.

This keeps the first implementation simple, uses Django fixtures for their intended cross-database portability, still
surfaces drift risk, and avoids relying on the old server's SQLite CLI.

## Prompts

### Original prompt

```text
Goal: create a _PLAN_ for a script to export all db schema/data via python, so that a clean db can be recreated/repopulated via a fixture.

Context:

- For some of my django projects, I haven't always been good about using migrations. Therefore it's possible that some elements of a database are slightly out-of-sync with the code/models.

- I'll be switching this webapp to use an sqlite-db on our dev-server, from a mysql-db.

- I want to ensure that I transfer all of the db-data over properly, including some admin super-users.

- We don't have access to a modern sqlite-CLI on the old dev-server -- it's using a newer-version of sqlite that's embedded in a `uv`-installed version of python.

- I'd like to be able to run a script that does multiple things, depending on options:
	- saves to some appropriate file-format (json?) the schema of the db.
	- saves to some appropriate file-format (sql? or json for a fixture?) _all_ the essential info for a new db to be repopulated, regardless of whether that new-db is mysql or sqlite.
	- creates a new sqlite-db from the saved export, above.

- I don't have a preference for whether the script is a django management-command, or a script stored, say, in the `usepweb_project/misc/` directory.

Tasks:

- make a plan to create a script that do the above.

- review `usepweb_project/AGENTS.md` for coding directives to follow.

- Feel free to suggest questions, or issues to resolve first, if that'll assist in the development of a plan for the script.

- Append this prompt to an `## Original prompt` section at the bottom of the plan.

- Save the plan to `usepweb_project/misc/PLAN__db_export_import_script.md`
```

### Subsequent review

After the original plan was drafted, we made these changes:

- Added a table of contents linking to the main `##` sections.
- Changed the implementation runtime guidance to follow `pyproject.toml` (`>=3.8,<3.9`) instead of the Python 3.12 target
  mentioned in `AGENTS.md`.
- Moved export output outside the Git-committed project, defaulting to `../db_exports` from the project root and
  auto-creating that directory when needed.
- Expanded the first use of DDL as "Data Definition Language".
- Renamed the proposed management command from `db_portable_snapshot` to `db_transfer_validation`.
- Simplified the first implementation to four subcommands: `export`, `import`, `inspect-drift`, and `validate`; other
  subcommands and options were moved to future-additions sections.
- Reframed the first implementation around Django fixtures rather than a raw MySQL-to-SQLite converter:
  `fixture.django.json` is the primary portable artifact, Django creates the SQLite schema, and fixture loading handles
  data import.
- Kept raw schema and row exports as audit/fallback artifacts rather than the normal import path.
- Resolved data-scope questions: exclude `django_session`, include `django_admin_log` row data as essential, assume
  no non-Django MySQL tables require preservation, scope the first version to MySQL source -> SQLite target, and generate
  JSONL row exports only when drift is detected.
