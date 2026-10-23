import tempfile
import unittest
from pathlib import Path
from checkpoints import checkpoint_directory, session_id


class CheckpointTests(unittest.TestCase):
    def test_resume_keeps_source_readonly_and_state_separate(self):
        from ocr_engine import command
        args = command('/fixed/source', 'synthetic', '', mode='scan',
                       state_home='/private/state', resume='scan-123')
        self.assertIn('type=bind,source=/fixed/source,target=/review,readonly', args)
        self.assertIn('type=bind,source=/private/state,target=/tmp/home/.opencodereview', args)
        self.assertIn('--group-add', args)
        self.assertEqual(args[-2:], ['--resume', 'scan-123'])

    def test_identity_changes_with_commit_generation_and_model(self):
        with tempfile.TemporaryDirectory() as root:
            task = dict(name='task', head_sha='a', base_sha='', review_mode='scan')
            first = checkpoint_directory(Path(root), task, {'model': 'one'})
            self.assertEqual(first, checkpoint_directory(Path(root), task, {'model': 'one'}))
            for changed in ({**task, 'head_sha': 'b'}, {**task, 'checkpoint_generation': 1}):
                self.assertNotEqual(first, checkpoint_directory(Path(root), changed, {'model': 'one'}))
            self.assertNotEqual(first, checkpoint_directory(Path(root), task, {'model': 'two'}))

    def test_session_list_is_validated(self):
        self.assertEqual(session_id('[{"id":"scan-123"}]'), 'scan-123')
        self.assertIsNone(session_id('[]'))
        self.assertIsNone(session_id('null'))
        self.assertEqual(session_id('[{"session_id":"scan-123"}]'), 'scan-123')
        with self.assertRaises(ValueError):
            session_id('[{"id":"../escape"}]')
