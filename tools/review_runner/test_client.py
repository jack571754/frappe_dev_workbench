import json
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
import urllib.error

from client import Client


class ClientTests(unittest.TestCase):
    def test_heartbeat_retries_transient_connection_but_not_authorization(self):
        client = self.client({'message': {'status': 'running'}})
        response = client.opener.open.return_value
        client.opener.open.side_effect = [urllib.error.URLError('offline'), response]
        with patch('client.time.sleep'):
            self.assertEqual(client.call('heartbeat')['status'], 'running')
        self.assertEqual(client.opener.open.call_count, 2)
        client.opener.open.reset_mock()
        client.opener.open.side_effect = urllib.error.HTTPError('local', 403, 'denied', {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            client.call('heartbeat')
        self.assertEqual(client.opener.open.call_count, 1)

    def client(self, payload):
        client = Client('http://127.0.0.1:8000', 'synthetic')
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        client.opener.open = MagicMock(return_value=response)
        return client

    def test_empty_frappe_response_means_idle_only_for_claim(self):
        self.assertIsNone(self.client({}).call('claim_task'))
        self.assertIsNone(self.client({}).call('claim_repository_preparation'))
        with self.assertRaises(KeyError):
            self.client({}).call('heartbeat')

    def test_claim_result_and_unexpected_payload(self):
        self.assertEqual(self.client({'message': {'name': 'task'}}).call('claim_task'), {'name': 'task'})
        self.assertIsNone(self.client({'message': None}).call('claim_task'))
        with self.assertRaises(KeyError):
            self.client({'error': 'unexpected'}).call('claim_task')
