import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_provider import load_provider, settings_path


class ProviderTests(unittest.TestCase):
    def test_malformed_settings_are_configuration_error_without_secret_disclosure(self):
        from local_provider import ProviderConfigurationError
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'settings.json')
            path.write_text('{"env":{"ANTHROPIC_AUTH_TOKEN":"private-token"},\n"allow":["Bash", s]}', encoding='utf-8')
            with self.assertRaises(ProviderConfigurationError) as caught:
                load_provider(path)
            self.assertIn('第 2 行', str(caught.exception))
            self.assertNotIn('private-token', str(caught.exception))

    def test_reuses_only_model_configuration_never_hooks_or_oauth(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'settings.json')
            path.write_text(json.dumps({'model': 'opus', 'env': {
                'ANTHROPIC_BASE_URL': 'https://model.example.invalid',
                'ANTHROPIC_AUTH_TOKEN': 'synthetic-token',
                'ANTHROPIC_DEFAULT_OPUS_MODEL': 'vendor-model',
                'CODEUP_ACCESS_TOKEN': 'must-not-forward',
                'CLAUDE_CODE_OAUTH_TOKEN': 'must-not-forward'},
                'hooks': {'dangerous': 'must-not-load'}, 'permissions': {'allow': ['Bash']}}), encoding='utf-8')
            env = load_provider(str(path))
            self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'], 'synthetic-token')
            self.assertEqual(env['ANTHROPIC_BASE_URL'], 'https://model.example.invalid')
            self.assertEqual(env['ANTHROPIC_MODEL'], 'opus')
            self.assertNotIn('CLAUDE_CODE_OAUTH_TOKEN', env)
            self.assertNotIn('CODEUP_ACCESS_TOKEN', env)
            self.assertNotIn('hooks', env)

    def test_missing_third_party_configuration_fails_without_official_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'settings.json')
            path.write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_provider(str(path))

    def test_windows_path_conversion_stays_inside_linux(self):
        self.assertEqual(str(settings_path('C:\\Users\\name\\.claude\\settings.json')),
                         '/mnt/c/Users/name/.claude/settings.json')
