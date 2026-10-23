"""数据目录解析与旧数据迁移的单元测试（不依赖 frappe / docker）。"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import paths


class DataRootTest(unittest.TestCase):
    def test_explicit_override_wins(self):
        self.assertEqual(paths.data_root('/tmp/workbench'), Path('/tmp/workbench'))
        self.assertEqual(paths.data_root('~/workbench'), Path('~/workbench').expanduser())

    def test_environment_override(self):
        with mock.patch.dict(os.environ, {'DEV_WORKBENCH_HOME': '/tmp/env-workbench'}):
            self.assertEqual(paths.data_root(), Path('/tmp/env-workbench'))

    def test_default_is_outside_project(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DEV_WORKBENCH_HOME', None)
            resolved = paths.data_root().resolve()
            self.assertNotEqual(resolved, paths.TOOL_ROOT.resolve())
            self.assertFalse(str(resolved).startswith(str(paths.TOOL_ROOT)))

    def test_config_path_follows_root(self):
        self.assertEqual(paths.config_path('/data'), Path('/data/config.json'))
        self.assertEqual(paths.config_path(), paths.data_root() / 'config.json')


class MigrateTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='paths-test-'))
        self.legacy = self.base / 'legacy'
        self.target = self.base / 'target'
        self.legacy.mkdir()
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _seed(self):
        (self.legacy / 'config.json').write_text('{"url": "http://127.0.0.1:8000"}', encoding='utf-8')
        (self.legacy / 'repositories' / 'demo').mkdir(parents=True)

    def test_migrates_config_and_cache(self):
        self._seed()
        with mock.patch.object(paths, 'LEGACY_ROOT', self.legacy):
            moved = paths.migrate(self.target)
        self.assertIn('config.json', moved)
        self.assertIn('repositories', moved)
        self.assertTrue((self.target / 'config.json').is_file())
        self.assertTrue((self.target / 'repositories' / 'demo').is_dir())
        self.assertFalse((self.legacy / 'config.json').exists())

    def test_second_run_is_noop(self):
        self._seed()
        with mock.patch.object(paths, 'LEGACY_ROOT', self.legacy):
            self.assertIn('config.json', paths.migrate(self.target))
            self.assertEqual(paths.migrate(self.target), [])

    def test_never_overwrites_existing_target(self):
        self._seed()
        (self.target / 'config.json').write_text('{"keep": true}', encoding='utf-8')
        with mock.patch.object(paths, 'LEGACY_ROOT', self.legacy):
            moved = paths.migrate(self.target)
        self.assertNotIn('config.json', moved)
        self.assertEqual((self.target / 'config.json').read_text(encoding='utf-8'), '{"keep": true}')

    def test_missing_legacy_is_noop(self):
        with mock.patch.object(paths, 'LEGACY_ROOT', self.base / 'absent'):
            self.assertEqual(paths.migrate(self.target), [])

    def test_same_directory_is_skipped(self):
        with mock.patch.object(paths, 'LEGACY_ROOT', self.target):
            self.assertEqual(paths.migrate(self.target), [])


class ConversionTest(unittest.TestCase):
    def test_windows_to_posix(self):
        self.assertEqual(paths.windows_to_posix('C:\\Users\\dev\\DevWorkbench'), '/mnt/c/Users/dev/DevWorkbench')
        self.assertEqual(paths.windows_to_posix('d:/data'), '/mnt/d/data')
        self.assertEqual(paths.windows_to_posix('C:\\'), '/mnt/c')
        self.assertIsNone(paths.windows_to_posix('/mnt/c/Users/dev'))
        self.assertIsNone(paths.windows_to_posix('relative/path'))

    def test_posix_to_windows(self):
        self.assertEqual(paths.posix_to_windows('/mnt/c/Users/dev'), 'C:\\Users\\dev')
        self.assertEqual(paths.posix_to_windows('/mnt/d'), 'D:\\')
        self.assertIsNone(paths.posix_to_windows('/home/dev'))

    def test_normalize_path_follows_platform(self):
        if sys.platform == 'win32':
            self.assertEqual(paths.normalize_path('/mnt/c/Users/dev'), 'C:\\Users\\dev')
        else:
            self.assertEqual(paths.normalize_path('C:\\Users\\dev'), '/mnt/c/Users/dev')
        self.assertEqual(paths.normalize_path(''), '')
        self.assertEqual(paths.normalize_path('  /srv/data  '), '/srv/data')

    def test_data_root_accepts_windows_path(self):
        resolved = paths.data_root('C:\\Users\\dev\\DevWorkbench')
        if sys.platform == 'win32':
            self.assertEqual(resolved, Path('C:\\Users\\dev\\DevWorkbench'))
        else:
            self.assertEqual(resolved, Path('/mnt/c/Users/dev/DevWorkbench'))


if __name__ == '__main__':
    unittest.main()
