import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import managed_repository as managed
import runner
from processes import run_process
from snapshot import prepare_materials


class ManagedRepositoryTests(unittest.TestCase):
    def test_rejects_symlinked_cache_without_touching_developer_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / 'developer'
            outside.mkdir()
            config_directory = root / 'runner'
            config_directory.mkdir()
            (config_directory / 'managed-repositories').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                managed.prepare(config_directory / 'config.json', 'repo', {
                    'url': 'https://codeup.aliyun.com/org/repo.git', 'access_token': 'secret'}, lambda: None)
            self.assertEqual(list(outside.iterdir()), [])

    def test_rejects_sources_that_could_expose_credentials(self):
        for url in ('file:///tmp/repo', 'http://codeup.aliyun.com/a.git', 'https://evil.invalid/a.git',
                    'https://user:secret@codeup.aliyun.com/a.git', 'https://codeup.aliyun.com:444/a.git',
                    'https://codeup.aliyun.com/a.git?token=secret'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                managed.validate_source_url(url)

    def test_prepare_and_sync_only_touch_managed_cache_and_preserve_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / 'developer-repo'
            remote.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(remote), *args], stderr=subprocess.DEVNULL).decode().strip()
            git('init'); git('config', 'user.name', 'Synthetic'); git('config', 'user.email', 'test@example.invalid')
            (remote / 'api.py').write_text('old\n')
            git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
            config_path = root / 'config.json'
            config_path.write_text(json.dumps({'token': 'workbench-secret', 'repositories': {'manual': str(remote)}}))
            source = {'url': 'https://codeup.aliyun.com/org/repo.git', 'access_token': 'git-secret'}
            def network(args, heartbeat, **kwargs):
                self.assertNotIn('git-secret', ' '.join(args))
                return run_process([str(remote) if a == source['url'] else a for a in args], heartbeat, **kwargs)
            with patch.object(managed, 'run_process', side_effect=network):
                outside_objects = root / 'outside-objects'
                outside_objects.mkdir()
                with patch.dict(os.environ, {'GIT_OBJECT_DIRECTORY': str(outside_objects), 'GIT_TRACE': str(root / 'trace')}):
                    target = managed.prepare(config_path, '../repo/中文', source, lambda: None)
                self.assertEqual(list(outside_objects.iterdir()), [])
                self.assertFalse((root / 'trace').exists())
                self.assertNotEqual(target, remote)
                (remote / 'api.py').write_text('new\n'); git('commit', '-qam', 'change'); head = git('rev-parse', 'HEAD')
                (remote / 'api.py').write_text('uncommitted\n')
                managed.sync(config_path, '../repo/中文', source, [head, base], lambda: None)
            data = json.loads(config_path.read_text())
            self.assertEqual(data['token'], 'workbench-secret')
            self.assertEqual(data['repositories']['manual'], str(remote))
            self.assertEqual((remote / 'api.py').read_text(), 'uncommitted\n')
            self.assertTrue(managed.is_managed(config_path, '../repo/中文', data['repositories']['../repo/中文']))
            self.assertFalse(managed.is_managed(config_path, 'manual', str(remote)))
            self.assertEqual(prepare_materials(target, base, head)['changes'][0]['new'], 'new\n')
            self.assertNotIn('git-secret', config_path.read_text())
            self.assertNotIn('git-secret', (target / 'config').read_text())
            class Client:
                def __init__(self):
                    self.materials = None
                def call(self, method, **params):
                    if method == 'repository_source':
                        return source
                    if method == 'upload_materials':
                        self.materials = params['materials']
                    return {}
            client = Client()
            config = {**data, 'snapshot_root': str(root / 'snapshots')}
            with patch.object(managed, 'run_process', side_effect=network), \
                    patch.object(runner, 'validate_model_configuration'), \
                    patch('ocr_engine.execute', return_value=({'findings': []}, 'synthetic')), \
                    patch.dict(os.environ, {'GIT_OBJECT_DIRECTORY': str(outside_objects), 'GIT_TRACE': str(root / 'trace')}):
                runner.execute(config, client, {'name': 'synthetic', 'lease_token': 'synthetic',
                    'repository': '../repo/中文', 'head_sha': head, 'base_sha': base}, config_path)
            self.assertIsNotNone(client.materials)
            self.assertEqual(client.materials['changes'][0]['new'], 'new\n')
            self.assertFalse((root / 'trace').exists())


if __name__ == '__main__':
    unittest.main()
