import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ocr_engine import build_repository, command, provider_environment, normalize_report


class OCRTests(unittest.TestCase):
    def test_unmapped_alias_is_a_configuration_error(self):
        from local_provider import ProviderConfigurationError
        with tempfile.TemporaryDirectory() as root:
            source = Path(root, 'settings.json')
            source.write_text(json.dumps({'model': 'fable', 'env': {
                'ANTHROPIC_BASE_URL': 'https://proxy.example.invalid',
                'ANTHROPIC_AUTH_TOKEN': 'synthetic', 'ANTHROPIC_MODEL': 'vendor-model'}}))
            with self.assertRaises(ProviderConfigurationError):
                provider_environment({'claude_settings_file': str(source)})

    def test_provider_maps_cli_alias_and_never_uses_official_default(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root, 'settings.json')
            source.write_text(json.dumps({'model': 'opus', 'env': {
                'ANTHROPIC_BASE_URL': 'https://proxy.example.invalid/v1',
                'ANTHROPIC_AUTH_TOKEN': 'synthetic', 'ANTHROPIC_DEFAULT_OPUS_MODEL': 'vendor-opus'}}))
            env = provider_environment({'claude_settings_file': str(source)})
            self.assertEqual(env['OCR_LLM_URL'], 'https://proxy.example.invalid/v1/messages')
            self.assertEqual(env['OCR_LLM_MODEL'], 'vendor-opus')
            self.assertEqual(env['OCR_LLM_AUTH_HEADER'], 'authorization')
            self.assertNotIn('CLAUDE_CODE_OAUTH_TOKEN', env)
            data = json.loads(source.read_text())
            data['model'] = 'fable'
            data['env']['ANTHROPIC_DEFAULT_FABLE_MODEL'] = 'vendor-fable'
            source.write_text(json.dumps(data))
            self.assertEqual(provider_environment({'claude_settings_file': str(source)})['OCR_LLM_MODEL'], 'vendor-fable')

    def test_normalization_preserves_partial_coverage_and_critical_severity(self):
        payload = {'status': 'partial', 'comments': [{'path': 'api.py', 'start_line': 2,
            'end_line': 3, 'content': '权限遗漏', 'existing_code': 'return data', 'severity': 'critical'}],
            'manifest': {'coverage': {'completed': [{'path': 'api.py'}], 'reused': [],
                'failed': [{'path': 'other.py', 'reason': 'timeout'}], 'waived': []}}}
        result = normalize_report(payload, {'api.py': {'new': 5}, 'other.py': {'new': 3}})
        self.assertEqual(result['findings'][0]['severity'], 'high')
        self.assertTrue(result['partial'])
        self.assertEqual(result['coverage']['reviewed'], ['api.py'])
        self.assertEqual(result['coverage']['skipped'][0]['path'], 'other.py')
        with self.assertRaises(ValueError):
            normalize_report({'status': 'failed', 'comments': []}, {})

    def test_large_report_keeps_reviewable_results_and_explicit_limit(self):
        payload = {'status': 'complete', 'comments': [{'path': 'api.py', 'start_line': 1,
            'end_line': 1, 'content': 'issue ' + str(i), 'severity': 'medium'} for i in range(201)],
            'manifest': {'coverage': {'completed': [{'path': 'api.py'}]}}}
        result = normalize_report(payload, {'api.py': {'new': 1}})
        self.assertEqual(len(result['findings']), 200)
        self.assertTrue(result['partial'])
        self.assertIn('201', ' '.join(result['limitations']))

    def test_empty_report_without_coverage_is_not_a_clean_bill(self):
        result = normalize_report({'status': 'success', 'comments': []}, {'api.py': {'new': 3}})
        self.assertTrue(result['partial'])

    def test_mode_only_changes_survive_reconstruction(self):
        for old_mode, new_mode in [('100755', '100644'), ('100644', '100755')]:
            with self.subTest(old_mode=old_mode), tempfile.TemporaryDirectory() as root:
                materials = {'manifest': {'run.sh': {'old_exists': True, 'new_exists': True,
                    'old_mode': old_mode, 'new_mode': new_mode}}, 'files': [],
                    'changes': [{'path': 'run.sh', 'old': 'echo ok\n', 'new': 'echo ok\n', 'skipped': ''}]}
                sha = build_repository(root, materials)
                raw = subprocess.check_output(['git', '-C', root, 'diff', '--raw', sha+'^', sha], text=True)
                self.assertIn(':' + old_mode + ' ' + new_mode, raw)

    def test_container_is_readonly_and_uses_explicit_commit(self):
        args = command('/tmp/repo', 'test', 'a' * 40)
        self.assertIn('--read-only', args)
        self.assertIn('type=bind,source=/tmp/repo,target=/review,readonly', args)
        self.assertIn('--commit', args)
        self.assertEqual(args[args.index('--max-tokens-budget') + 1], '0')
        self.assertNotIn('--output', args)
        self.assertIn('json', args)
        self.assertNotIn('synthetic-secret', ' '.join(args))

    def test_synthetic_repository_has_only_requested_diff_and_safe_context(self):
        with tempfile.TemporaryDirectory() as root:
            material = {'manifest': {'api.py': {'old': 1, 'new': 1, 'old_exists': True, 'new_exists': True}},
                'changes': [{'path': 'api.py', 'old': 'old\n', 'new': 'new\n', 'skipped': ''}],
                'files': [{'path': 'context/caller.py', 'content': 'call()\n'},
                          {'path': 'context/.opencodereview/config.json', 'content': 'untrusted'}]}
            sha = build_repository(Path(root), material)
            paths = subprocess.check_output(['git', '-C', root, 'diff', '--name-only', sha+'^', sha], text=True).splitlines()
            self.assertEqual(paths, ['api.py'])
            self.assertTrue(Path(root, 'caller.py').exists())
            self.assertFalse(Path(root, '.opencodereview').exists())


if __name__ == '__main__':
    unittest.main()
