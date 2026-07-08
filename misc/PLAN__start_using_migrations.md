# Plan: Start Using Django Migrations Safely

Goal: introduce Django migrations as a baseline for the existing schema, with minimal risk of data loss.

## Core Principle

Treat the first migration as a record of the schema that already exists, not as a schema change.

Do not run a plain `migrate` against production first. For a legacy database with existing tables, the first migration should usually be applied with `--fake-initial`.

## Steps

1. Work from the actual git repo directory:

   ```bash
   cd usepweb_project
   ```

2. Generate the initial migration locally:

   ```bash
   uv run python manage.py makemigrations usep_app
   ```

   This should create a file like:

   ```text
   usep_app/migrations/0001_initial.py
   ```

   This command creates migration files only. It does not touch the database.

3. Inspect what Django thinks it would create:

   ```bash
   uv run python manage.py sqlmigrate usep_app 0001
   ```

4. Compare that SQL against the real database schema.

   Expected existing table names will likely include:

   ```text
   usep_app_flatcollection
   usep_app_aboutpage
   usep_app_textspage
   usep_app_linkspage
   usep_app_contactspage
   usep_app_publicationspage
   ```

5. Before running anything against real data, take a database backup and test on a restored copy.

   For MySQL:

   original recommendation...

   ```bash
   mysqldump --single-transaction --routines --triggers DB_NAME > before_migrations.sql
   ```

   updated recommendation after i showed codex our sysadmin recommendation:

    ```bash
    /standard/odd/path/to/mysqldump \
        --user=THE_USER \
        --host=THE_HOST \
        --enable-cleartext-plugin \
        -p \
        --single-transaction \
        --skip-lock-tables \
        --routines \
        --triggers \
        --events \
        --no-tablespaces \
        DB_NAME > /path/to/before_migrations.sql
    ```

   For SQLite: copy the database file while the app is stopped.

6. On the copied or staging database, run:

   ```bash
   uv run python manage.py migrate --fake-initial
   ```

   `--fake-initial` tells Django to record the initial migration as applied if the existing tables match the migration, instead of trying to create those tables again.

7. Verify the staging database and application behavior.

   Suggested checks:

   ```bash
   uv run python manage.py showmigrations usep_app
   uv run python manage.py check
   ```

   Also verify the relevant application pages and admin screens.

8. Commit the generated migration file.

   ```bash
   git status --short
   git add usep_app/migrations/0001_initial.py
   git commit -m "Add initial migration baseline"
   ```

9. Only after staging succeeds, repeat the backup and fake-initial migration on production:

   ```bash
   uv run python manage.py migrate --fake-initial
   ```

## Future Model Changes

After the baseline migration is in place, future schema changes should follow the normal Django migration workflow:

```bash
uv run python manage.py makemigrations
uv run python manage.py sqlmigrate APP_NAME MIGRATION_NAME
uv run python manage.py migrate
```

For any change that could affect existing data, take a backup first and test the migration on a restored copy before production.
