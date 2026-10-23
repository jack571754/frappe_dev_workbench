import json
import unittest
from unittest.mock import MagicMock

from client import Client


class ClientTests(unittest.TestCase):
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
