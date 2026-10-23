import unittest
import urllib.error
from unittest.mock import Mock, patch

import runner


class SyncRetryTests(unittest.TestCase):
    def test_source_socket_timeout_is_retried(self):
        client = Mock()
        client.call.side_effect = [TimeoutError(), {'url': 'safe'}]
        with patch.object(runner, 'sync_cache'), patch.object(runner.time, 'sleep'):
            runner.synchronize_repository('config', client, {'name': 'task', 'lease_token': 'lease',
                'repository': 'repo', 'head_sha': 'a' * 40, 'base_sha': ''}, lambda: None)
        self.assertEqual(client.call.call_count, 2)
    def test_temporary_source_failure_is_retried_before_syncing_fixed_versions(self):
        client = Mock()
        client.call.side_effect = [urllib.error.URLError('temporary'), {'url': 'safe'}]
        heartbeat = Mock()
        with patch.object(runner, 'sync_cache', return_value='cache') as sync, patch.object(runner.time, 'sleep'):
            runner.synchronize_repository('config', client, {'name': 'task', 'lease_token': 'lease',
                'repository': 'repo', 'head_sha': 'a' * 40, 'base_sha': ''}, heartbeat)
        self.assertEqual(client.call.call_count, 2)
        self.assertEqual(sync.call_args.args[3], ['a' * 40, ''])

    def test_authentication_failure_is_not_retried(self):
        client = Mock()
        client.call.side_effect = urllib.error.HTTPError('private', 403, 'denied', {}, None)
        with self.assertRaises(RuntimeError), patch.object(runner.time, 'sleep'):
            runner.synchronize_repository('config', client, {'name': 'task', 'lease_token': 'lease',
                'repository': 'repo', 'head_sha': 'a' * 40, 'base_sha': ''}, lambda: None)
        self.assertEqual(client.call.call_count, 1)

    def test_git_failure_is_bounded_to_three_attempts(self):
        client = Mock()
        client.call.return_value = {'url': 'safe'}
        with patch.object(runner, 'sync_cache', side_effect=RuntimeError('execution')) as sync, \
                patch.object(runner.time, 'sleep'), self.assertRaises(RuntimeError):
            runner.synchronize_repository('config', client, {'name': 'task', 'lease_token': 'lease',
                'repository': 'repo', 'head_sha': 'a' * 40, 'base_sha': ''}, lambda: None)
        self.assertEqual(sync.call_count, 3)
