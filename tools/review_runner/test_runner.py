import json
import tempfile
import unittest
import subprocess
from pathlib import Path

from sandbox import command, write_materials
from snapshot import prepare_materials
from preflight import probe_evidence


class SandboxTests(unittest.TestCase):
    def test_preflight_requires_tool_evidence_not_model_claim(self):
        self.assertFalse(probe_evidence(json.dumps({'type': 'system', 'message': 'provider notice'})))
        for result in ('PREFLIGHT_OK; outside reading was not denied', 'PREFLIGHT_OK denied'):
            self.assertFalse(probe_evidence(json.dumps({'type': 'result', 'result': result})))
        events = [
            {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'id': 'read1', 'name': 'Read', 'input': {'file_path': '/review/sample.py'}},
                {'type': 'tool_use', 'id': 'read2', 'name': 'Read', 'input': {'file_path': '/etc/hostname'}}]}},
            {'type': 'user', 'message': {'content': [
                {'type': 'tool_result', 'tool_use_id': 'read1', 'content': 'def divide(a, b):\n    return a / b'},
                {'type': 'tool_result', 'tool_use_id': 'read2', 'is_error': True, 'content': 'denied'}]}},
        ]
        self.assertTrue(probe_evidence('\n'.join(map(json.dumps, events))))
        events[1]['message']['content'][1]['is_error'] = False
        self.assertFalse(probe_evidence('\n'.join(map(json.dumps, events))))
    def test_sandbox_is_readonly_and_has_no_host_secrets(self):
        cmd = command('/tmp/snapshot', 'test-container', 'review-image')
        self.assertIn('--read-only', cmd)
        self.assertIn('--cap-drop=ALL', cmd)
        self.assertIn('--security-opt=no-new-privileges', cmd)
        self.assertIn('type=bind,source=/tmp/snapshot,target=/review,readonly', cmd)
        self.assertNotIn('--privileged', cmd)
        self.assertIn('Read,Glob,Grep', cmd)
        self.assertIn('--restricted', cmd)
        self.assertIn('--safe-mode', cmd)
        self.assertNotIn('Bash', cmd)

    def test_materials_reject_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            for path in ('../secret', '/etc/passwd', 'C:/secret', 'a\\b', '.git/config'):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    write_materials(Path(root), {'files': [{'path': path, 'content': 'x'}]})


class SnapshotTests(unittest.TestCase):
    def test_versions_include_deleted_lines_and_ignore_worktree(self):
        with tempfile.TemporaryDirectory() as root:
            def git(*args):
                return subprocess.check_output(['git', '-C', root, *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.name', 'Synthetic')
            git('config', 'user.email', 'synthetic@example.invalid')
            Path(root, 'api.py').write_text('old\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            Path(root, 'api.py').write_text('new\nsecond\n', encoding='utf-8')
            git('commit', '-qam', 'change')
            head = git('rev-parse', 'HEAD')
            Path(root, 'api.py').write_text('UNCOMMITTED SECRET', encoding='utf-8')
            materials = prepare_materials(root, base, head)
            self.assertEqual(materials['manifest']['api.py']['old'], 1)
            self.assertEqual(materials['manifest']['api.py']['new'], 2)
            self.assertNotIn('UNCOMMITTED', json.dumps(materials))
            self.assertIn('-old', materials['changes'][0]['diff'])
            with self.assertRaises(ValueError):
                prepare_materials(root, '', head)


if __name__ == '__main__':
    unittest.main()
