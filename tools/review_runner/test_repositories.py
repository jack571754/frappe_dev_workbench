import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import repositories
import runner


class RepositoryTests(unittest.TestCase):
    def test_configured_path_must_be_repository_root_not_arbitrary_child(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / 'working'
            subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
            child = repo / 'source'
            child.mkdir()
            result = repositories.check_repositories({'root': str(repo), 'child': str(child)})
            self.assertEqual(result, {'root': 'ready', 'child': 'unavailable'})

    def test_status_reporting_reloads_mapping_during_an_active_review(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / 'repo.git'
            subprocess.run(['git', 'init', '--bare', str(repo)], check=True, capture_output=True)
            config_path = Path(root) / 'config.json'
            config_path.write_text(json.dumps({'repositories': {'new': str(repo)}, 'token': 'changed'}))
            config = {'repositories': {}, 'token': 'original'}
            class Client:
                def call(self, method, **params):
                    self.method, self.params = method, params
            client = Client()
            runner.report_repository_status(config, client, config_path)
            self.assertEqual(client.method, 'report_repositories')
            self.assertEqual(client.params['repositories'], {'new': 'ready'})
            self.assertEqual(config['token'], 'original')

    def test_only_readable_git_repositories_are_ready(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / '中文 repo.git'
            subprocess.run(['git', 'init', '--bare', str(repo)], check=True, capture_output=True)
            result = repositories.check_repositories({'valid': str(repo), 'missing': root + '/absent', 'plain': root})
            self.assertEqual(result, {'valid': 'ready', 'missing': 'unavailable', 'plain': 'unavailable'})

    def test_configure_preserves_credentials_and_rejects_non_git_directory(self):
        with tempfile.TemporaryDirectory() as root:
            config = Path(root) / 'config.json'
            config.write_text(json.dumps({'token': 'keep-private', 'repositories': {'old': '/old'}}))
            with self.assertRaises(ValueError):
                repositories.configure(config, 'new', root)
            repo = Path(root) / '仓库.git'
            subprocess.run(['git', 'init', '--bare', str(repo)], check=True, capture_output=True)
            repositories.configure(config, 'new', str(repo))
            data = json.loads(config.read_text())
            self.assertEqual(data['token'], 'keep-private')
            self.assertEqual(data['repositories'], {'old': '/old', 'new': str(repo)})


if __name__ == '__main__':
    unittest.main()
