import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import environment
import runner


class ModelConfigurationTests(unittest.TestCase):
    def test_scan_has_independent_optional_deadline(self):
        self.assertEqual(runner.task_timeout_seconds({'timeout_seconds': 1200}, {'review_mode': 'scan'}), 0)
        self.assertEqual(runner.task_timeout_seconds({'timeout_seconds': 1200}, {'review_mode': 'commit'}), 1200)
        self.assertEqual(runner.task_timeout_seconds({'scan_timeout_seconds': 7200}, {'review_mode': 'scan'}), 7200)
        self.assertEqual(runner.task_timeout_seconds({'scan_timeout_seconds': 0}, {'review_mode': 'scan'}), 0)

    def test_unlimited_scan_still_sends_heartbeat_and_accepts_cancellation(self):
        with tempfile.TemporaryDirectory() as root:
            config = {'snapshot_root': root, 'repositories': {'repo': root}}
            client = Mock()
            client.call.side_effect = RuntimeError('cancelled')
            materials = '{"manifest":{},"changes":[]}'
            clock = [0, 0, 100000, 100000, 100000]
            def engine(config, materials, repository_root, container, heartbeat):
                heartbeat()
            with patch.object(runner, 'validate_model_configuration'), \
                    patch.object(runner.time, 'monotonic', side_effect=clock), \
                    patch.object(runner, 'is_managed', return_value=False), \
                    patch.object(runner, 'run_process', return_value=materials), \
                    patch('ocr_engine.execute', side_effect=engine):
                # upload_materials succeeds; the later heartbeat rejects cancellation.
                client.call.side_effect = [None, RuntimeError('cancelled'), None]
                runner.execute(config, client, {'name': 'task', 'lease_token': 'lease',
                    'repository': 'repo', 'base_sha': '', 'head_sha': 'a' * 40, 'review_mode': 'scan'})
            self.assertIn('heartbeat', [call.args[0] for call in client.call.call_args_list])
            self.assertNotIn('upload_report', [call.args[0] for call in client.call.call_args_list])

    def test_invalid_configuration_fails_before_reading_repository_and_has_safe_diagnostic(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root, 'settings.json')
            source.write_text('{"secret":"do-not-disclose", "env": s}', encoding='utf-8')
            config = {'claude_settings_file': str(source), 'snapshot_root': str(Path(root, 'snapshots'))}
            client = Mock()
            with patch.object(runner, 'run_process') as process:
                runner.execute(config, client, {'name': 'task', 'lease_token': 'lease', 'repository': 'repo'})
            process.assert_not_called()
            params = client.call.call_args.kwargs
            self.assertEqual(params['error'], 'model_configuration')
            self.assertIn('第 1 行', params['raw_report'])
            self.assertNotIn('do-not-disclose', params['raw_report'])

    def test_environment_checks_contents_instead_of_file_existence(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root, 'settings.json')
            source.write_text('{"env": s}', encoding='utf-8')
            with patch.object(environment, '_first_line', return_value='installed'), \
                    patch.object(environment, '_image_exists', return_value=True):
                result = environment.collect({'claude_settings_file': str(source)}, root=root)
            check = next(item for item in result['checks'] if item['check'] == 'model_settings')
            self.assertFalse(check['passed'])
            self.assertIn('JSON', check['detail'])
