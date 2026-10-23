"""仓库准备的真实数据库协议测试，事务回滚且不访问外部仓库。"""
import json
import unittest
from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime
from dev_workbench.api.v1 import code_review as api


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.user = frappe.session.user
        frappe.set_user('Administrator')
        frappe.db.savepoint('preparation_tests')
        self.repo = api._insert('Codeup Repository', repository_name='synthetic-' + frappe.generate_hash(length=10),
                                repo_id='synthetic', is_active=1)
        self.executor = api._insert(api.EXECUTOR, label='synthetic', enabled=1, token_hash=api._hash('y' * 40))
        self.auth = patch.object(api, '_executor', return_value=self.executor.name)
        self.auth.start()
        api.report_repositories({}, supports_preparation=1)

    def tearDown(self):
        self.auth.stop()
        frappe.db.rollback(save_point='preparation_tests')
        frappe.set_user(self.user)

    def test_request_is_deduplicated_and_lease_is_bound_to_executor(self):
        first = api.prepare_repository(self.repo.name, self.executor.name)
        self.assertEqual(api.prepare_repository(self.repo.name, self.executor.name)['name'], first['name'])
        claim = api.claim_repository_preparation()
        self.assertEqual(claim['name'], first['name'])
        self.assertEqual(claim['repository'], self.repo.name)
        self.assertNotIn('access_token', claim)
        with self.assertRaises(frappe.PermissionError):
            api.preparation_heartbeat(claim['name'], 'invalid')
        with patch.object(api, '_executor', return_value='different-executor'):
            with self.assertRaises(frappe.PermissionError):
                api.repository_source(claim['name'], claim['lease_token'], preparation=1)
        self.assertIsNone(api.claim_task('synthetic'))
        api.preparation_heartbeat(claim['name'], claim['lease_token'])
        api.finish_repository_preparation(claim['name'], claim['lease_token'], success=1)
        self.assertEqual(frappe.db.get_value(api.PREPARATION, first['name'], 'status'), 'completed')

    def test_offline_or_old_executor_cannot_receive_preparation(self):
        api.report_repositories({})
        with self.assertRaises(frappe.ValidationError):
            api.prepare_repository(self.repo.name, self.executor.name)
        api.report_repositories({}, supports_preparation=1)
        frappe.db.set_value(api.EXECUTOR, self.executor.name, 'capabilities_at', add_to_date(now_datetime(), seconds=-121))
        with self.assertRaises(frappe.ValidationError):
            api.prepare_repository(self.repo.name, self.executor.name)

    def test_manager_access_is_required_before_requesting_download(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            api.prepare_repository(self.repo.name, self.executor.name)

    def test_source_only_available_for_a_valid_lease_and_not_in_public_readiness(self):
        api.prepare_repository(self.repo.name, self.executor.name)
        claim = api.claim_repository_preparation()
        source = {'url': 'https://codeup.aliyun.com/org/repo.git', 'access_token': 'private-token'}
        with patch.object(api, '_repository_source', return_value=source):
            self.assertEqual(api.repository_source(claim['name'], claim['lease_token'], preparation=1), source)
            with self.assertRaises(frappe.PermissionError):
                api.repository_source(claim['name'], 'incorrect', preparation=1)
        readiness = json.dumps(api.repository_readiness(), default=str)
        self.assertNotIn('private-token', readiness)
        self.assertNotIn('lease_token', readiness)

    def test_expired_preparation_can_be_retried_but_cannot_upload_late_success(self):
        first = api.prepare_repository(self.repo.name, self.executor.name)
        claim = api.claim_repository_preparation()
        frappe.db.set_value(api.PREPARATION, claim['name'], 'lease_until', add_to_date(now_datetime(), seconds=-1))
        second = api.prepare_repository(self.repo.name, self.executor.name)
        self.assertNotEqual(first['name'], second['name'])
        with self.assertRaises(frappe.PermissionError):
            api.finish_repository_preparation(claim['name'], claim['lease_token'], success=1)


def run_checks():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PreparationTests))
    if not result.wasSuccessful():
        raise RuntimeError('仓库准备集成测试失败')
    return {'tests': result.testsRun, 'passed': True}
