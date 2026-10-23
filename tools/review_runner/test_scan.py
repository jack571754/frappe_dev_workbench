import subprocess
import tempfile
import unittest
from pathlib import Path
from snapshot import prepare_scan_materials
from ocr_engine import command, build_repository

class ScanTests(unittest.TestCase):
    def test_scan_reads_fixed_tree_including_unchanged_files(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*args):
                return subprocess.check_output(['git', '-C', d, *args], stderr=subprocess.DEVNULL).decode().strip()
            git('init'); git('config', 'user.name', 'test'); git('config', 'user.email', 'test@example.invalid')
            Path(d, 'api.py').write_text('old = 1\n')
            Path(d, '.env').write_text('SECRET=synthetic')
            Path(d, 'node_modules').mkdir(); Path(d, 'node_modules/x.js').write_text('generated')
            git('add', '.'); git('commit', '-qm', 'base')
            Path(d, 'other.py').write_text('new = 2\n'); git('add', '.'); git('commit', '-qm', 'head')
            sha = git('rev-parse', 'HEAD')
            Path(d, 'api.py').write_text('uncommitted = 3\n')
            m = prepare_scan_materials(d, sha)
            changes = {c['path']: c for c in m['changes']}
            self.assertEqual(changes['api.py']['new'], 'old = 1\n')
            self.assertEqual(changes['other.py']['new'], 'new = 2\n')
            self.assertTrue(changes['.env']['skipped'])
            self.assertTrue(changes['node_modules/x.js']['skipped'])
            self.assertEqual(m['mode'], 'scan')
            with tempfile.TemporaryDirectory() as out:
                build_repository(out, m)
                self.assertFalse(Path(out, '.env').exists())
                self.assertFalse(Path(out, 'node_modules').exists())

    def test_scan_command_has_no_commit_diff_and_no_token_cap(self):
        args = command('/tmp/repo', 'test', 'a'*40, mode='scan')
        self.assertIn('scan', args)
        self.assertNotIn('--commit', args)
        self.assertEqual(args[args.index('--max-tokens-budget')+1], '0')
