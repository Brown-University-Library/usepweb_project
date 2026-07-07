# -*- coding: utf-8 -*-

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

from usep_app import models
from usep_app.management.commands import db_transfer_validation


class DbTransferValidationHelperTest(TestCase):
    """ Checks db-transfer helper behavior. """

    def test_redact_database_settings_hides_secret_values(self):
        """ Checks database setting redaction hides credentials and host details. """
        redacted = db_transfer_validation.redact_database_settings(
            {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': 'usep',
                'USER': 'dbuser',
                'PASSWORD': 'secret',
                'HOST': 'db.example.edu',
                'OPTIONS': {'ssl': True},
            }
        )

        self.assertEqual('usep', redacted['NAME'])
        self.assertEqual('[redacted]', redacted['USER'])
        self.assertEqual('[redacted]', redacted['PASSWORD'])
        self.assertEqual('[redacted]', redacted['HOST'])
        self.assertEqual('[redacted]', redacted['OPTIONS'])

    def test_output_parent_refuses_project_directory_without_override(self):
        """ Checks export output refuses the Git project directory by default. """
        project_root = Path(__file__).resolve().parent.parent

        with self.assertRaises(CommandError):
            db_transfer_validation.resolve_output_parent(str(project_root / 'tmp-export'), False)

    def test_expected_index_signatures_include_unique_model_fields(self):
        """ Checks expected index signatures use columns and uniqueness rather than generated names. """
        expected_signatures = db_transfer_validation.build_expected_index_signature_map()
        username_signature = (('username',), True)

        self.assertIn('auth_user', expected_signatures)
        self.assertIn(username_signature, expected_signatures['auth_user'])
        self.assertIn('auth.User.username unique field', expected_signatures['auth_user'][username_signature]['sources'])


class DbTransferValidationCommandTest(TestCase):
    """ Checks db_transfer_validation management-command workflows. """

    def setUp(self):
        """ Creates rows that should round-trip through the fixture. """
        user_model = get_user_model()
        user_model.objects.create_superuser(username='admin-test', email='admin@example.edu', password='secret')
        collection = models.FlatCollection(
            collection_code='RI.TEST.1',
            region_code='RI',
            region_name='Rhode Island',
            collection_name='Rhode Island Test Collection',
        )
        collection.save()

    def test_export_writes_core_artifacts_and_superuser_fixture(self):
        """ Checks export writes manifest, schema, fixture, and checksums. """
        with tempfile.TemporaryDirectory() as temp_dir:
            call_command('db_transfer_validation', 'export', '--output-dir', temp_dir, stdout=StringIO(), verbosity=0)
            export_dir = self.get_single_export_dir(temp_dir)

            self.assertTrue((export_dir / 'manifest.json').exists())
            self.assertTrue((export_dir / 'schema.json').exists())
            self.assertTrue((export_dir / 'schema-source.sql').exists())
            self.assertTrue((export_dir / 'fixture.django.json').exists())
            self.assertTrue((export_dir / 'checksums.json').exists())

            manifest = json.loads((export_dir / 'manifest.json').read_text(encoding='utf-8'))
            fixture = json.loads((export_dir / 'fixture.django.json').read_text(encoding='utf-8'))

            self.assertIn('auth_user', manifest['transfer_table_counts'])
            self.assertIn('usep_app_flatcollection', manifest['transfer_table_counts'])
            self.assertNotIn('django_session', manifest['fixture_tables'])
            self.assertTrue(self.fixture_contains_superuser(fixture, 'admin-test'))

    def test_import_refuses_existing_sqlite_without_drop_flag(self):
        """ Checks import protects an existing SQLite target unless explicitly overridden. """
        with tempfile.TemporaryDirectory() as temp_dir:
            call_command('db_transfer_validation', 'export', '--output-dir', temp_dir, stdout=StringIO(), verbosity=0)
            export_dir = self.get_single_export_dir(temp_dir)
            sqlite_path = Path(temp_dir) / 'target.sqlite3'
            sqlite_path.write_text('', encoding='utf-8')

            with self.assertRaises(CommandError):
                call_command(
                    'db_transfer_validation',
                    'import',
                    '--input-dir',
                    str(export_dir),
                    '--sqlite-path',
                    str(sqlite_path),
                    verbosity=0,
                )

    def test_import_creates_sqlite_database_and_preserves_superuser(self):
        """ Checks import creates a SQLite database and validates transferred rows. """
        with tempfile.TemporaryDirectory() as temp_dir:
            call_command('db_transfer_validation', 'export', '--output-dir', temp_dir, stdout=StringIO(), verbosity=0)
            export_dir = self.get_single_export_dir(temp_dir)
            sqlite_path = Path(temp_dir) / 'target.sqlite3'

            call_command(
                'db_transfer_validation',
                'import',
                '--input-dir',
                str(export_dir),
                '--sqlite-path',
                str(sqlite_path),
                stdout=StringIO(),
                verbosity=0,
            )

            report = json.loads((export_dir / 'import-report.json').read_text(encoding='utf-8'))
            self.assertTrue(sqlite_path.exists())
            self.assertTrue(report['ok'])
            self.assertIn('admin-test', report['admin_state']['superuser_usernames'])

    def get_single_export_dir(self, parent_dir):
        """ Checks and returns the only export directory in a temp parent. """
        children = [path for path in Path(parent_dir).iterdir() if path.is_dir()]
        self.assertEqual(1, len(children))
        return children[0]

    def fixture_contains_superuser(self, fixture, username):
        """ Checks whether fixture data contains the expected superuser. """
        contains_superuser = False
        for item in fixture:
            if item.get('model') == 'auth.user':
                fields = item.get('fields', {})
                if fields.get('username') == username and fields.get('is_superuser'):
                    contains_superuser = True
                    break
        return contains_superuser
