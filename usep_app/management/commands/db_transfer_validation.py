# -*- coding: utf-8 -*-
"""
Exports, imports, and validates database-transfer artifacts for this Django project.

Purpose
-------

This command supports moving the USEP webapp database from an existing live database, currently expected to be MySQL in
older environments, into a clean Django-managed database such as SQLite, for our dev-server and for local development.
It is intentionally Django-aware: it uses Django settings, registered models, database introspection, serializers,
migrations, and fixture loading instead of shelling out to database command-line tools.

The command treats the live database as the schema source of truth for audit purposes. That matters because this legacy
project has not always had complete migrations for every model change. During export, the command captures the live
schema and compares it with the current registered Django models so an operator can see whether a standard fixture-based
transfer is likely to be complete.

Transfer model
--------------

The normal transfer path is fixture-centered:

1. `export` writes Django model data to `fixture.django.json`.
2. `import` creates the target SQLite schema through Django's migration/syncdb path.
3. `import` loads `fixture.django.json` through Django's fixture loader.
4. `validate` compares expected model-backed table counts and admin/superuser state.

Raw schema and row artifacts are audit/fallback artifacts, not the standard importer input. `schema.json` and
`schema-source.sql` preserve what the source database looked like. If schema/model drift is detected, raw JSONL files are
also written under `data/` so rows from drifted or unexpected tables/columns can be inspected manually.

Default artifacts
-----------------

Exports are written to timestamped directories under `../db_exports` from the project root unless `--output-dir` is
provided. The command refuses to write export artifacts inside the Git project directory unless
`--force-in-repo-output` is passed.

Typical export files:

- `manifest.json`: export metadata, row counts, redacted database settings, and drift summary
- `fixture.django.json`: portable Django fixture for model-backed data
- `schema.json`: structured live-schema introspection and model/schema comparison
- `schema-source.sql`: source-backend Data Definition Language for reference
- `checksums.json`: SHA-256 checksums for exported artifacts
- `import-report.json`: validation report written after import
- `data/*.jsonl`: raw table rows, only generated when drift is detected

Usage
-----

Run through Django's management command interface:

```bash
uv run ./manage.py db_transfer_validation --help
uv run ./manage.py db_transfer_validation inspect-drift --database default
uv run ./manage.py db_transfer_validation export --database default --output-dir ../db_exports
uv run ./manage.py db_transfer_validation import --input-dir ../db_exports/EXPORT_DIR --sqlite-path /path/to/new.sqlite3
uv run ./manage.py db_transfer_validation validate --input-dir ../db_exports/EXPORT_DIR --sqlite-path /path/to/new.sqlite3
```

`import` will not overwrite an existing SQLite target unless `--drop-existing-sqlite` is provided. The import path uses
Django's SQLite backend and does not require the external `sqlite3` command-line tool.
"""

import base64
import datetime
import decimal
import hashlib
import json
import os
import platform
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import django
from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import DEFAULT_DB_ALIAS, connections

COMMAND_NAME = 'db_transfer_validation'
EXPORT_FORMAT_VERSION = 1
IMPORT_DATABASE_ALIAS = 'db_transfer_import_target'
DEFAULT_EXCLUDED_TABLES = ['django_session']
DEFAULT_EXCLUDED_MODEL_LABELS = ['sessions.Session']
KNOWN_NONMODEL_TABLES = ['django_migrations']
SECRET_DATABASE_SETTING_KEYS = ['PASSWORD', 'HOST', 'USER', 'OPTIONS']


class Command(BaseCommand):
    """
    Exports, imports, and validates portable database transfer artifacts.
    """

    help = 'Exports schema/data artifacts and imports Django fixtures into a managed SQLite database.'

    def add_arguments(self, parser: Any) -> None:
        """
        Adds command-line arguments.

        Called by: django.core.management.BaseCommand.create_parser()
        """
        subparsers = parser.add_subparsers(dest='subcommand', required=True)

        export_parser = subparsers.add_parser('export', help='Write schema, fixture, manifest, and checksum artifacts.')
        export_parser.add_argument('--database', default=DEFAULT_DB_ALIAS)
        export_parser.add_argument('--output-dir', default=None)
        export_parser.add_argument('--batch-size', default=1000, type=int)
        export_parser.add_argument('--force-in-repo-output', action='store_true', default=False)

        import_parser = subparsers.add_parser('import', help='Create a Django-managed SQLite database and load a fixture.')
        import_parser.add_argument('--input-dir', required=True)
        import_parser.add_argument('--sqlite-path', required=True)
        import_parser.add_argument('--drop-existing-sqlite', action='store_true', default=False)

        drift_parser = subparsers.add_parser('inspect-drift', help='Report live-schema/model drift.')
        drift_parser.add_argument('--database', default=DEFAULT_DB_ALIAS)

        validate_parser = subparsers.add_parser('validate', help='Compare an export against a database.')
        validate_parser.add_argument('--input-dir', required=True)
        validate_parser.add_argument('--database', default=DEFAULT_DB_ALIAS)
        validate_parser.add_argument('--sqlite-path', default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Routes the selected subcommand to its implementation.

        Called by: django.core.management.BaseCommand.execute()
        """
        subcommand = options['subcommand']
        verbosity = int(options.get('verbosity', 1))

        if subcommand == 'export':
            export_dir = run_export(
                database_alias=options['database'],
                output_dir=options.get('output_dir'),
                batch_size=options['batch_size'],
                force_in_repo_output=options['force_in_repo_output'],
                verbosity=verbosity,
            )
            self.stdout.write('Export written to %s' % export_dir)
        elif subcommand == 'import':
            report = run_import(
                input_dir=Path(options['input_dir']),
                sqlite_path=Path(options['sqlite_path']),
                drop_existing_sqlite=options['drop_existing_sqlite'],
                verbosity=verbosity,
            )
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        elif subcommand == 'inspect-drift':
            report = run_inspect_drift(database_alias=options['database'])
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
            if report['has_drift']:
                raise CommandError('Schema/model drift was found.')
        elif subcommand == 'validate':
            report = run_validate(
                input_dir=Path(options['input_dir']),
                database_alias=options['database'],
                sqlite_path=Path(options['sqlite_path']) if options.get('sqlite_path') else None,
            )
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
            if not report['ok']:
                raise CommandError('Validation failed.')


def run_export(
    database_alias: str,
    output_dir: Optional[str],
    batch_size: int,
    force_in_repo_output: bool,
    verbosity: int,
) -> Path:
    """
    Writes all first-version export artifacts to a timestamped directory.

    Called by: Command.handle()
    """
    connection = connections[database_alias]
    output_parent = resolve_output_parent(output_dir, force_in_repo_output)
    export_dir = make_export_directory(output_parent, database_alias)
    table_names = list_table_names(connection)
    row_counts = collect_row_counts(connection, table_names)
    schema_report = collect_schema_report(connection, table_names)
    drift_report = schema_report['model_comparison']
    schema_source_sql = collect_schema_source_sql(connection, table_names)
    fixture_path = export_dir / 'fixture.django.json'

    write_json(export_dir / 'schema.json', schema_report)
    (export_dir / 'schema-source.sql').write_text(schema_source_sql, encoding='utf-8')
    write_fixture(fixture_path, database_alias, verbosity)

    raw_data_checksums = {}
    raw_data_tables = []
    if drift_report['has_drift']:
        raw_data_tables = [table for table in table_names if table not in DEFAULT_EXCLUDED_TABLES]
        raw_data_checksums = export_raw_table_rows(
            connection, export_dir / 'data', raw_data_tables, schema_report, batch_size
        )

    checksums = build_checksums(export_dir, raw_data_checksums)
    write_json(export_dir / 'checksums.json', checksums)

    manifest = build_manifest(
        connection=connection,
        database_alias=database_alias,
        table_names=table_names,
        row_counts=row_counts,
        output_options={
            'output_dir': str(output_parent),
            'batch_size': batch_size,
            'force_in_repo_output': force_in_repo_output,
        },
        drift_report=drift_report,
        raw_data_tables=raw_data_tables,
    )
    write_json(export_dir / 'manifest.json', manifest)
    return export_dir


def run_import(input_dir: Path, sqlite_path: Path, drop_existing_sqlite: bool, verbosity: int) -> Dict[str, Any]:
    """
    Creates a SQLite database through Django migrations and loads the exported fixture.

    Called by: Command.handle()
    """
    input_dir = input_dir.resolve()
    sqlite_path = sqlite_path.resolve()
    fixture_path = input_dir / 'fixture.django.json'

    if not fixture_path.exists():
        raise CommandError('Fixture does not exist: %s' % fixture_path)
    if sqlite_path.exists() and not drop_existing_sqlite:
        raise CommandError('SQLite target already exists; pass --drop-existing-sqlite to overwrite it: %s' % sqlite_path)
    if sqlite_path.exists() and drop_existing_sqlite:
        sqlite_path.unlink()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        configure_sqlite_database_alias(IMPORT_DATABASE_ALIAS, sqlite_path)
        call_command('migrate', database=IMPORT_DATABASE_ALIAS, run_syncdb=True, interactive=False, verbosity=verbosity)
        call_command('loaddata', str(fixture_path), database=IMPORT_DATABASE_ALIAS, verbosity=verbosity)

        report = build_validation_report(input_dir, connections[IMPORT_DATABASE_ALIAS])
        write_json(input_dir / 'import-report.json', report)
        if not report['ok']:
            raise CommandError('Import completed, but validation failed. See %s' % (input_dir / 'import-report.json'))
    finally:
        remove_database_alias(IMPORT_DATABASE_ALIAS)
    return report


def run_inspect_drift(database_alias: str) -> Dict[str, Any]:
    """
    Builds a schema/model drift report for the selected database.

    Called by: Command.handle()
    """
    connection = connections[database_alias]
    table_names = list_table_names(connection)
    schema_report = collect_schema_report(connection, table_names)
    report = schema_report['model_comparison']
    return report


def run_validate(input_dir: Path, database_alias: str, sqlite_path: Optional[Path]) -> Dict[str, Any]:
    """
    Compares an export directory against a configured database or SQLite file.

    Called by: Command.handle()
    """
    input_dir = input_dir.resolve()
    if sqlite_path is not None:
        try:
            configure_sqlite_database_alias(IMPORT_DATABASE_ALIAS, sqlite_path.resolve())
            report = build_validation_report(input_dir, connections[IMPORT_DATABASE_ALIAS])
        finally:
            remove_database_alias(IMPORT_DATABASE_ALIAS)
    else:
        connection = connections[database_alias]
        report = build_validation_report(input_dir, connection)
    return report


def resolve_output_parent(output_dir: Optional[str], force_in_repo_output: bool) -> Path:
    """
    Resolves and validates the export parent directory.

    Called by: run_export()
    """
    project_root = Path(settings.BASE_DIR).resolve()
    if output_dir:
        output_parent = Path(output_dir)
        if not output_parent.is_absolute():
            output_parent = project_root / output_parent
    else:
        output_parent = project_root.parent / 'db_exports'

    output_parent = output_parent.resolve()
    if is_path_within(output_parent, project_root) and not force_in_repo_output:
        raise CommandError(
            'Refusing to write export artifacts inside the Git project directory without --force-in-repo-output: %s'
            % output_parent
        )
    output_parent.mkdir(parents=True, exist_ok=True)
    return output_parent


def is_path_within(child_path: Path, parent_path: Path) -> bool:
    """
    Returns whether a path is inside another path using Python 3.8-compatible APIs.

    Called by: resolve_output_parent()
    """
    is_within = False
    try:
        child_path.resolve().relative_to(parent_path.resolve())
        is_within = True
    except ValueError:
        is_within = False
    return is_within


def make_export_directory(output_parent: Path, database_alias: str) -> Path:
    """
    Creates a timestamped export directory.

    Called by: run_export()
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_alias = re.sub(r'[^A-Za-z0-9_.-]+', '-', database_alias).strip('-') or 'database'
    export_dir = output_parent / ('%s__%s' % (timestamp, safe_alias))
    suffix = 1
    while export_dir.exists():
        export_dir = output_parent / ('%s__%s-%s' % (timestamp, safe_alias, suffix))
        suffix += 1
    export_dir.mkdir(parents=True)
    return export_dir


def list_table_names(connection: Any) -> List[str]:
    """
    Lists database tables visible to Django introspection.

    Called by: run_export()
    """
    with connection.cursor() as cursor:
        table_names = sorted(connection.introspection.table_names(cursor))
    return table_names


def collect_row_counts(connection: Any, table_names: Sequence[str]) -> Dict[str, int]:
    """
    Counts rows in the supplied tables.

    Called by: run_export()
    """
    row_counts = {}
    with connection.cursor() as cursor:
        for table_name in table_names:
            cursor.execute('SELECT COUNT(*) FROM %s' % quote_identifier(connection, table_name))
            row_counts[table_name] = int(cursor.fetchone()[0])
    return row_counts


def collect_schema_report(connection: Any, table_names: Sequence[str]) -> Dict[str, Any]:
    """
    Collects structured schema details and a model/schema comparison.

    Called by: run_export()
    """
    tables = {}
    with connection.cursor() as cursor:
        table_types = collect_table_types(connection, cursor)
        for table_name in table_names:
            columns = collect_column_schema(connection, cursor, table_name)
            constraints = collect_constraints(connection, cursor, table_name)
            tables[table_name] = {
                'type': table_types.get(table_name),
                'columns': columns,
                'constraints': constraints,
            }
    schema_report = {
        'database_vendor': connection.vendor,
        'tables': tables,
        'model_comparison': compare_model_schema(tables),
    }
    return json_ready(schema_report)


def collect_table_types(connection: Any, cursor: Any) -> Dict[str, str]:
    """
    Collects table types when the backend exposes them.

    Called by: collect_schema_report()
    """
    table_types = {}
    for table_info in connection.introspection.get_table_list(cursor):
        table_types[table_info.name] = getattr(table_info, 'type', None)
    return table_types


def collect_column_schema(connection: Any, cursor: Any, table_name: str) -> List[Dict[str, Any]]:
    """
    Collects column metadata for a table.

    Called by: collect_schema_report()
    """
    columns = []
    description = connection.introspection.get_table_description(cursor, table_name)
    for column in description:
        database_type = None
        try:
            database_type = connection.introspection.get_field_type(column.type_code, column)
        except Exception:
            database_type = str(column.type_code)
        columns.append(
            {
                'name': column.name,
                'type_code': column.type_code,
                'database_type': database_type,
                'display_size': getattr(column, 'display_size', None),
                'internal_size': getattr(column, 'internal_size', None),
                'precision': getattr(column, 'precision', None),
                'scale': getattr(column, 'scale', None),
                'null_ok': getattr(column, 'null_ok', None),
                'default': getattr(column, 'default', None),
                'collation': getattr(column, 'collation', None),
            }
        )
    return columns


def collect_constraints(connection: Any, cursor: Any, table_name: str) -> Dict[str, Any]:
    """
    Collects constraints for a table using backend introspection.

    Called by: collect_schema_report()
    """
    constraints = {}
    try:
        constraints = connection.introspection.get_constraints(cursor, table_name)
    except NotImplementedError:
        constraints = {}
    return constraints


def compare_model_schema(tables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares live table/column names to registered Django model metadata.

    Called by: collect_schema_report()
    """
    live_table_names = set(tables.keys())
    model_table_map = build_model_table_map()
    model_table_names = set(model_table_map.keys())

    live_tables_without_models = sorted(live_table_names - model_table_names - set(KNOWN_NONMODEL_TABLES))
    model_tables_missing_from_live = sorted(model_table_names - live_table_names)
    live_columns_not_in_models = {}
    model_fields_missing_from_live = {}

    for table_name in sorted(live_table_names & model_table_names):
        live_columns = set(column['name'] for column in tables[table_name]['columns'])
        model_columns = set(model_table_map[table_name]['columns'])
        extra_columns = sorted(live_columns - model_columns)
        missing_columns = sorted(model_columns - live_columns)
        if extra_columns:
            live_columns_not_in_models[table_name] = extra_columns
        if missing_columns:
            model_fields_missing_from_live[table_name] = missing_columns

    has_drift = bool(
        live_tables_without_models
        or model_tables_missing_from_live
        or live_columns_not_in_models
        or model_fields_missing_from_live
    )
    comparison = {
        'has_drift': has_drift,
        'model_tables': sorted(model_table_names),
        'live_tables': sorted(live_table_names),
        'ignored_live_tables_without_models': sorted(set(live_table_names) & set(KNOWN_NONMODEL_TABLES)),
        'live_tables_without_models': live_tables_without_models,
        'model_tables_missing_from_live': model_tables_missing_from_live,
        'live_columns_not_in_models': live_columns_not_in_models,
        'model_fields_missing_from_live': model_fields_missing_from_live,
    }
    return comparison


def build_model_table_map() -> Dict[str, Dict[str, Any]]:
    """
    Maps registered concrete model tables to labels and column names.

    Called by: compare_model_schema()
    """
    model_table_map = {}
    for model in apps.get_models(include_auto_created=True):
        columns = []
        for field in model._meta.concrete_fields:
            if field.column:
                columns.append(field.column)
        model_table_map[model._meta.db_table] = {
            'label': model._meta.label,
            'columns': sorted(columns),
        }
    return model_table_map


def collect_schema_source_sql(connection: Any, table_names: Sequence[str]) -> str:
    """
    Collects backend-native Data Definition Language where supported.

    Called by: run_export()
    """
    if connection.vendor == 'mysql':
        sql_text = collect_mysql_schema_source_sql(connection, table_names)
    elif connection.vendor == 'sqlite':
        sql_text = collect_sqlite_schema_source_sql(connection)
    else:
        sql_text = '-- Native schema-source SQL capture is not implemented for backend vendor: %s\n' % connection.vendor
    return sql_text


def collect_mysql_schema_source_sql(connection: Any, table_names: Sequence[str]) -> str:
    """
    Collects MySQL SHOW CREATE TABLE output.

    Called by: collect_schema_source_sql()
    """
    statements = []
    with connection.cursor() as cursor:
        for table_name in table_names:
            cursor.execute('SHOW CREATE TABLE %s' % quote_identifier(connection, table_name))
            row = cursor.fetchone()
            statements.append('-- %s' % table_name)
            statements.append(row[1])
            statements.append('')
    return '\n'.join(statements)


def collect_sqlite_schema_source_sql(connection: Any) -> str:
    """
    Collects SQLite sqlite_master SQL definitions.

    Called by: collect_schema_source_sql()
    """
    statements = []
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL
            ORDER BY type, name
            """
        )
        for row in cursor.fetchall():
            statements.append('-- %s %s on %s' % (row[0], row[1], row[2]))
            statements.append(row[3] + ';')
            statements.append('')
    return '\n'.join(statements)


def write_fixture(fixture_path: Path, database_alias: str, verbosity: int) -> None:
    """
    Writes the portable Django fixture for registered model data.

    Called by: run_export()
    """
    model_labels = get_fixture_model_labels()
    call_command(
        'dumpdata',
        *model_labels,
        database=database_alias,
        exclude=DEFAULT_EXCLUDED_MODEL_LABELS,
        natural_foreign=True,
        natural_primary=True,
        indent=2,
        output=str(fixture_path),
        verbosity=verbosity,
    )


def get_fixture_model_labels() -> List[str]:
    """
    Lists concrete model labels included in the portable fixture.

    Called by: write_fixture()
    """
    excluded_labels = set(DEFAULT_EXCLUDED_MODEL_LABELS)
    model_labels = []
    for model in apps.get_models(include_auto_created=False):
        if model._meta.label not in excluded_labels:
            model_labels.append(model._meta.label)
    return sorted(model_labels)


def export_raw_table_rows(
    connection: Any,
    data_dir: Path,
    table_names: Sequence[str],
    schema_report: Dict[str, Any],
    batch_size: int,
) -> Dict[str, str]:
    """
    Writes JSONL audit exports for all non-excluded live tables.

    Called by: run_export()
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    checksums = {}
    with connection.cursor() as cursor:
        for table_name in table_names:
            file_path = data_dir / ('%s.jsonl' % table_name)
            column_names = [column['name'] for column in schema_report['tables'][table_name]['columns']]
            order_column = find_primary_order_column(table_name, schema_report)
            sql = build_select_all_sql(connection, table_name, order_column)
            cursor.execute(sql)
            with file_path.open('w', encoding='utf-8') as output_file:
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    for row in rows:
                        output_file.write(json.dumps(json_ready(dict(zip(column_names, row))), sort_keys=True) + '\n')
            checksums[str(file_path.relative_to(data_dir.parent))] = sha256_file(file_path)
    return checksums


def find_primary_order_column(table_name: str, schema_report: Dict[str, Any]) -> Optional[str]:
    """
    Finds a stable primary-key order column when one is available.

    Called by: export_raw_table_rows()
    """
    order_column = None
    constraints = schema_report['tables'][table_name]['constraints']
    for constraint in constraints.values():
        if constraint.get('primary_key') and constraint.get('columns'):
            order_column = constraint['columns'][0]
            break
    if order_column is None:
        column_names = [column['name'] for column in schema_report['tables'][table_name]['columns']]
        if 'id' in column_names:
            order_column = 'id'
    return order_column


def build_select_all_sql(connection: Any, table_name: str, order_column: Optional[str]) -> str:
    """
    Builds a quoted SELECT statement for raw table export.

    Called by: export_raw_table_rows()
    """
    sql = 'SELECT * FROM %s' % quote_identifier(connection, table_name)
    if order_column is not None:
        sql = '%s ORDER BY %s' % (sql, quote_identifier(connection, order_column))
    return sql


def build_checksums(export_dir: Path, raw_data_checksums: Dict[str, str]) -> Dict[str, Any]:
    """
    Builds checksum metadata for core and optional raw export files.

    Called by: run_export()
    """
    checksums = {
        'fixture.django.json': sha256_file(export_dir / 'fixture.django.json'),
        'schema.json': sha256_file(export_dir / 'schema.json'),
        'schema-source.sql': sha256_file(export_dir / 'schema-source.sql'),
        'data': raw_data_checksums,
    }
    return checksums


def build_manifest(
    connection: Any,
    database_alias: str,
    table_names: Sequence[str],
    row_counts: Dict[str, int],
    output_options: Dict[str, Any],
    drift_report: Dict[str, Any],
    raw_data_tables: Sequence[str],
) -> Dict[str, Any]:
    """
    Builds self-describing export metadata.

    Called by: run_export()
    """
    manifest = {
        'export_format_version': EXPORT_FORMAT_VERSION,
        'export_timestamp': datetime.datetime.now().isoformat(),
        'project_name': 'usep-web-project',
        'django_version': django.get_version(),
        'python_version': platform.python_version(),
        'database_alias': database_alias,
        'database_vendor': connection.vendor,
        'source_database': redact_database_settings(connection.settings_dict),
        'installed_apps': list(settings.INSTALLED_APPS),
        'command': COMMAND_NAME,
        'command_options': output_options,
        'tables': list(table_names),
        'row_counts': row_counts,
        'transfer_table_counts': build_transfer_table_counts(row_counts),
        'excluded_tables': DEFAULT_EXCLUDED_TABLES,
        'excluded_model_labels': DEFAULT_EXCLUDED_MODEL_LABELS,
        'fixture_model_labels': get_fixture_model_labels(),
        'fixture_tables': get_transfer_table_names(),
        'raw_data_tables': list(raw_data_tables),
        'drift': drift_report,
    }
    return json_ready(manifest)


def build_transfer_table_counts(row_counts: Dict[str, int]) -> Dict[str, int]:
    """
    Builds row counts for tables expected to transfer through the fixture.

    Called by: build_manifest()
    """
    transfer_table_names = set(get_transfer_table_names())
    transfer_table_counts = {}
    for table_name, row_count in row_counts.items():
        if table_name in transfer_table_names:
            transfer_table_counts[table_name] = row_count
    return transfer_table_counts


def get_transfer_table_names() -> List[str]:
    """
    Lists model-backed tables expected to round-trip through the fixture.

    Called by: build_transfer_table_counts()
    """
    excluded_labels = set(DEFAULT_EXCLUDED_MODEL_LABELS)
    table_names = []
    for model in apps.get_models(include_auto_created=True):
        if model._meta.auto_created:
            table_names.append(model._meta.db_table)
        elif model._meta.label not in excluded_labels:
            table_names.append(model._meta.db_table)
    return sorted(set(table_names))


def redact_database_settings(database_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redacts secrets and host/account details from Django database settings.

    Called by: build_manifest()
    """
    redacted = {}
    for key, value in database_settings.items():
        if key in SECRET_DATABASE_SETTING_KEYS:
            redacted[key] = '[redacted]' if value else value
        else:
            redacted[key] = value
    return json_ready(redacted)


def configure_sqlite_database_alias(database_alias: str, sqlite_path: Path) -> None:
    """
    Adds or replaces a Django database alias for a SQLite transfer target.

    Called by: run_import()
    """
    database_config = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(sqlite_path),
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'OPTIONS': {},
        'TIME_ZONE': None,
        'TEST': {
            'CHARSET': None,
            'COLLATION': None,
            'MIGRATE': True,
            'MIRROR': None,
            'NAME': None,
        },
    }
    remove_database_alias(database_alias)
    settings.DATABASES[database_alias] = database_config
    connections.databases[database_alias] = database_config


def remove_database_alias(database_alias: str) -> None:
    """
    Removes the internal temporary database alias from Django connections.

    Called by: run_import()
    """
    if database_alias in connections:
        connections[database_alias].close()
        del connections[database_alias]
    settings.DATABASES.pop(database_alias, None)
    connections.databases.pop(database_alias, None)


def build_validation_report(input_dir: Path, connection: Any) -> Dict[str, Any]:
    """
    Compares exported row counts and essential admin-user state to a database.

    Called by: run_import()
    """
    manifest_path = input_dir / 'manifest.json'
    if not manifest_path.exists():
        raise CommandError('Manifest does not exist: %s' % manifest_path)

    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    live_tables = list_table_names(connection)
    live_counts = collect_row_counts(connection, live_tables)
    expected_counts = manifest.get('transfer_table_counts', {})
    count_mismatches = build_count_mismatches(expected_counts, live_counts)
    missing_tables = sorted(set(expected_counts.keys()) - set(live_tables))
    admin_state = collect_admin_user_state(connection)
    fixture_state = collect_fixture_user_state(input_dir / 'fixture.django.json')
    superuser_usernames_missing = sorted(set(fixture_state['superuser_usernames']) - set(admin_state['superuser_usernames']))

    ok = not count_mismatches and not missing_tables and not superuser_usernames_missing
    report = {
        'ok': ok,
        'database_vendor': connection.vendor,
        'database_name': connection.settings_dict.get('NAME'),
        'missing_tables': missing_tables,
        'count_mismatches': count_mismatches,
        'admin_state': admin_state,
        'fixture_state': fixture_state,
        'superuser_usernames_missing': superuser_usernames_missing,
    }
    return json_ready(report)


def build_count_mismatches(expected_counts: Dict[str, int], live_counts: Dict[str, int]) -> Dict[str, Dict[str, int]]:
    """
    Builds a table-count mismatch report.

    Called by: build_validation_report()
    """
    count_mismatches = {}
    for table_name, expected_count in expected_counts.items():
        live_count = live_counts.get(table_name)
        if live_count != expected_count:
            count_mismatches[table_name] = {
                'expected': expected_count,
                'actual': live_count,
            }
    return count_mismatches


def collect_admin_user_state(connection: Any) -> Dict[str, Any]:
    """
    Collects admin-user and superuser state from the target database.

    Called by: build_validation_report()
    """
    user_model = apps.get_model('auth', 'User')
    users = user_model.objects.using(connection.alias).all().order_by('username')
    state = {
        'user_count': users.count(),
        'superuser_count': users.filter(is_superuser=True).count(),
        'superuser_usernames': list(users.filter(is_superuser=True).values_list('username', flat=True)),
    }
    return state


def collect_fixture_user_state(fixture_path: Path) -> Dict[str, Any]:
    """
    Collects expected user state from the exported Django fixture.

    Called by: build_validation_report()
    """
    data = json.loads(fixture_path.read_text(encoding='utf-8'))
    user_count = 0
    superuser_usernames = []
    for item in data:
        if item.get('model') == 'auth.user':
            user_count += 1
            fields = item.get('fields', {})
            if fields.get('is_superuser'):
                superuser_usernames.append(fields.get('username'))
    state = {
        'user_count': user_count,
        'superuser_count': len(superuser_usernames),
        'superuser_usernames': sorted(superuser_usernames),
    }
    return state


def quote_identifier(connection: Any, identifier: str) -> str:
    """
    Quotes a database identifier for the active backend.

    Called by: collect_row_counts()
    """
    return connection.ops.quote_name(identifier)


def write_json(path: Path, data: Any) -> None:
    """
    Writes JSON with stable formatting.

    Called by: run_export()
    """
    path.write_text(json.dumps(json_ready(data), indent=2, sort_keys=True) + '\n', encoding='utf-8')


def sha256_file(path: Path) -> str:
    """
    Computes a SHA-256 checksum for a file.

    Called by: build_checksums()
    """
    digest = hashlib.sha256()
    with path.open('rb') as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def json_ready(value: Any) -> Any:
    """
    Converts backend-specific values into JSON-serializable values.

    Called by: write_json()
    """
    if isinstance(value, dict):
        ready_value = {}
        for key, item in value.items():
            ready_value[str(key)] = json_ready(item)
    elif isinstance(value, (list, tuple)):
        ready_value = [json_ready(item) for item in value]
    elif isinstance(value, set):
        ready_value = sorted(json_ready(item) for item in value)
    elif isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        ready_value = value.isoformat()
    elif isinstance(value, decimal.Decimal):
        ready_value = str(value)
    elif isinstance(value, bytes):
        ready_value = {'__bytes_base64__': base64.b64encode(value).decode('ascii')}
    elif isinstance(value, Path):
        ready_value = str(value)
    elif value is None or isinstance(value, (str, int, float, bool)):
        ready_value = value
    else:
        ready_value = str(value)
    return ready_value


def main() -> None:
    """
    Provides a simple script-style entry point for direct invocation.

    Called by: module guard
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.core.management import execute_from_command_line

    execute_from_command_line([sys.argv[0], COMMAND_NAME] + sys.argv[1:])


if __name__ == '__main__':
    main()
