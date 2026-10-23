"""运行于 bench 环境；事务回滚，不创建真实审查或调用外部模型。"""

import json
import unittest
from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime
from dev_workbench.api.v1 import code_review as api


class ReviewApiTests(unittest.TestCase):
    def setUp(self):
        self.user = frappe.session.user
        frappe.set_user('Administrator')
        frappe.db.savepoint('review_tests')
        self.executor = api._insert(api.EXECUTOR, label='synthetic', enabled=1,
                                    token_hash=api._hash('x' * 40))
        self.task = api._insert(api.TASK, title='synthetic', status='queued', review_status='pending',
                                head_sha='a' * 40, base_sha='')
        self.auth = patch.object(api, '_executor', return_value=self.executor.name)
        self.auth.start()
        frappe.db.set_value(api.TASK, self.task.name, 'repository', 'synthetic')
        api.report_repositories({'synthetic': 'ready'})

    def tearDown(self):
        self.auth.stop()
        frappe.db.rollback(save_point='review_tests')
        frappe.set_user(self.user)

    def claim(self):
        # 避免测试领取当前 site 的真实排队任务。
        with patch.object(api.frappe.db, 'sql', wraps=frappe.db.sql) as sql:
            original = sql._mock_wraps
            def scoped(query, *args, **kwargs):
                if query.startswith("select name from `tabCode Review Task` where status='queued'"):
                    return [(self.task.name,)]
                return original(query, *args, **kwargs)
            sql.side_effect = scoped
            return api.claim_task('synthetic')

    def test_full_scan_fixes_branch_sha_and_keeps_mode_distinct(self):
        from types import SimpleNamespace
        repo = SimpleNamespace(name='synthetic', is_active=1, repo_id='1')
        with patch.object(api, '_require_repositories'), \
                patch.object(api.frappe, 'get_doc', return_value=repo), \
                patch('dev_workbench.services.token_service.get_codeup_credentials', return_value={
                    'access_token': 'synthetic', 'base_url': 'https://example.invalid', 'org_id': '1'}), \
                patch('dev_workbench.services.codeup_client.CodeupClient') as client, \
                patch.object(api, '_insert', return_value=SimpleNamespace(name='scan-task')) as insert, \
                patch.object(api.frappe.db, 'get_value', return_value=None):
            client.return_value.list_commits.return_value = [{'id': 'b' * 40}]
            self.assertEqual(api.create_scan_task('synthetic', 'main'), 'scan-task')
            self.assertEqual(insert.call_args.kwargs['head_sha'], 'b' * 40)
            self.assertEqual(insert.call_args.kwargs['review_mode'], 'scan')
            self.assertEqual(insert.call_args.kwargs['base_sha'], '')
            self.assertEqual(insert.call_args.kwargs['branch'], 'main')
            repo.is_active = 0
            with self.assertRaises(frappe.ValidationError):
                api.create_scan_task('synthetic', 'main')

    def test_scan_claim_and_large_raw_report_roundtrip(self):
        frappe.db.set_value(api.TASK, self.task.name, 'review_mode', 'scan')
        claim = self.claim()
        self.assertEqual(claim['review_mode'], 'scan')
        material = {'mode': 'scan', 'head_sha': 'a' * 40, 'base_sha': '',
                    'manifest': {'api.py': {'old': 0, 'new': 2}}, 'files': []}
        api.upload_materials(self.task.name, claim['lease_token'], material)
        report = {'schema_version': 1, 'summary': 'synthetic full scan', 'findings': [],
                  'coverage': {'reviewed': ['api.py'], 'skipped': []}, 'limitations': []}
        raw = 'synthetic' + 'x' * 1_000_001
        api.upload_report(self.task.name, claim['lease_token'], report, raw)
        self.assertEqual(api.get_task(self.task.name)['attempt']['raw_report'], raw)

    def test_single_active_claim_and_expired_lease(self):
        claim = self.claim()
        self.assertEqual(claim['name'], self.task.name)
        self.assertIsNone(self.claim())
        api.heartbeat(claim['name'], claim['lease_token'])
        frappe.db.set_value(api.ATTEMPT, claim['attempt'], 'lease_until',
                            add_to_date(now_datetime(), seconds=-1))
        self.assertEqual(api.get_task(self.task.name)['status'], 'interrupted')
        listed = api.list_tasks()['tasks']
        self.assertEqual(next(t for t in listed if t.name == self.task.name).status, 'interrupted')
        with self.assertRaises(frappe.PermissionError):
            api.heartbeat(claim['name'], claim['lease_token'])

    def test_cancel_rejects_late_results_and_retry_keeps_attempt(self):
        claim = self.claim()
        api.cancel_task(self.task.name)
        with self.assertRaises(frappe.ValidationError):
            api.fail_attempt(self.task.name, claim['lease_token'])
        api.retry_task(self.task.name)
        self.assertTrue(frappe.db.exists(api.ATTEMPT, claim['attempt']))
        self.assertFalse(frappe.db.get_value(api.TASK, self.task.name, 'current_attempt'))

    def test_private_access(self):
        task = self.task
        task.owner = 'another-manager@example.invalid'
        with patch.object(api, 'require_manager'), patch.object(api, '_admin', return_value=False):
            with self.assertRaises(frappe.PermissionError):
                api._visible(task)

    def test_missing_repository_blocks_batch_before_any_tasks_are_inserted(self):
        count = frappe.db.count(api.TASK)
        with self.assertRaisesRegex(frappe.ValidationError, '仓库.*设置'):
            api.create_tasks([{'repository': 'synthetic', 'sha': 'a' * 40, 'activity_log': 'absent'},
                              {'repository': 'not-configured', 'sha': 'b' * 40, 'activity_log': 'absent'}])
        self.assertEqual(frappe.db.count(api.TASK), count)

    def test_missing_repository_blocks_scan_before_remote_lookup(self):
        with self.assertRaisesRegex(frappe.ValidationError, '仓库.*设置'):
            api.create_scan_task('not-configured', 'main')

    def test_readiness_expires_and_revoked_executor_is_not_usable(self):
        api.report_repositories({'synthetic': 'ready'})
        self.assertEqual(api._repository_states(['synthetic'])['synthetic']['status'], 'ready')
        frappe.db.set_value(api.EXECUTOR, self.executor.name, 'capabilities_at', add_to_date(now_datetime(), seconds=-121))
        self.assertEqual(api._repository_states(['synthetic'])['synthetic']['status'], 'offline')
        api.report_repositories({'synthetic': 'ready'})
        frappe.db.set_value(api.EXECUTOR, self.executor.name, 'enabled', 0)
        self.assertNotEqual(api._repository_states(['synthetic'])['synthetic']['status'], 'ready')

    def test_retry_without_readiness_keeps_failed_attempt(self):
        claim = self.claim()
        api.fail_attempt(self.task.name, claim['lease_token'], 'missing_repository')
        frappe.db.set_value(api.TASK, self.task.name, 'repository', 'not-configured')
        with self.assertRaises(frappe.ValidationError):
            api.retry_task(self.task.name)
        task = api.get_task(self.task.name)
        self.assertEqual(task['status'], 'failed')
        self.assertEqual(task['current_attempt'], claim['attempt'])

    def test_model_configuration_error_is_not_reported_as_invalid_report(self):
        claim = self.claim()
        api.fail_attempt(self.task.name, claim['lease_token'], 'model_configuration',
                         raw_report='本机模型配置 JSON 格式错误：第 16 行，第 15 列')
        task = api.get_task(self.task.name)
        self.assertEqual(task['status'], 'failed')
        self.assertIn('本机模型配置无效', task['attempt']['error'])
        self.assertIn('第 16 行', task['attempt']['raw_report'])

    def test_executor_cannot_claim_an_unconfigured_repository(self):
        api.report_repositories({})
        self.assertIsNone(api.claim_task('synthetic'))

    def test_claim_filters_repository_and_mode_in_database(self):
        original = frappe.db.sql
        def scoped(query, values=(), *args, **kwargs):
            if query.startswith("select name from `tabCode Review Task` where status='queued'"):
                query = query.replace('order by creation', 'and name=%s order by creation')
                values = (*values, self.task.name)
            return original(query, values, *args, **kwargs)
        with patch.object(api.frappe.db, 'sql', side_effect=scoped):
            frappe.db.set_value(api.TASK, self.task.name, 'repository', 'not-configured')
            self.assertIsNone(api.claim_task('synthetic'))
            frappe.db.set_value(api.TASK, self.task.name, {'repository': 'synthetic', 'review_mode': 'scan'})
            api.report_repositories({'synthetic': 'ready'}, modes=['commit'])
            self.assertIsNone(api.claim_task('synthetic'))
            frappe.db.set_value(api.TASK, self.task.name, 'review_mode', 'commit')
            claim = api.claim_task('synthetic')
            self.assertEqual(claim['name'], self.task.name)

    def test_report_review_and_history(self):
        claim = self.claim()
        material = {'head_sha': 'a' * 40, 'base_sha': '',
                    'manifest': {'api.py': {'old': 0, 'new': 2}}, 'files': []}
        api.upload_materials(self.task.name, claim['lease_token'], material)
        report = {'schema_version': 1, 'summary': '未发现问题', 'findings': [],
                  'coverage': {'reviewed': ['api.py'], 'skipped': []}, 'limitations': []}
        api.upload_report(self.task.name, claim['lease_token'], report, 'synthetic')
        # 上传响应丢失后重传同一报告应成功，且不能重复创建问题。
        api.upload_report(self.task.name, claim['lease_token'], report, 'synthetic')
        self.assertEqual(frappe.db.get_value(api.TASK, self.task.name, 'status'), 'completed')
        self.assertEqual(frappe.db.get_value(api.TASK, self.task.name, 'review_status'), 'pending')
        api.complete_review(self.task.name)
        api.retry_task(self.task.name)
        history = api.get_task(self.task.name, claim['attempt'])
        self.assertEqual(history['attempt']['raw_report'], 'synthetic')

    def test_retry_reclaims_expired_task_without_waiting_for_executor(self):
        claim = self.claim()
        frappe.db.set_value(api.ATTEMPT, claim['attempt'], 'lease_until',
                            add_to_date(now_datetime(), seconds=-1))
        api.retry_task(self.task.name)
        self.assertEqual(frappe.db.get_value(api.TASK, self.task.name, 'status'), 'queued')

    def test_finding_must_be_confirmed_before_completing_review(self):
        claim = self.claim()
        api.upload_materials(self.task.name, claim['lease_token'], {'head_sha': 'a' * 40, 'base_sha': '',
            'manifest': {'api.py': {'old': 0, 'new': 3}}, 'files': []})
        api.upload_report(self.task.name, claim['lease_token'], {'schema_version': 1, 'summary': '需复核',
            'findings': [{'severity': 'high', 'title': '权限校验遗漏', 'path': 'api.py', 'side': 'new',
                'line': 2, 'end_line': 3, 'trigger': '普通成员调用', 'impact': '私有记录泄露',
                'evidence': '直接返回全部记录', 'suggestion': '限制查询范围', 'uncertainty': ''}],
            'coverage': {'reviewed': ['api.py'], 'skipped': []}, 'limitations': []})
        with self.assertRaises(frappe.ValidationError):
            api.complete_review(self.task.name)
        finding = frappe.db.get_value(api.FINDING, {'task': self.task.name}, 'name')
        api.update_finding(finding, 'confirmed', '线下核实', feedback=1)
        self.assertEqual(frappe.db.get_value(api.FINDING, finding, 'note'), '线下核实')
        api.complete_review(self.task.name)
        self.assertEqual(frappe.db.get_value(api.TASK, self.task.name, 'review_status'), 'completed')

    def test_retention_deletes_only_old_finished_task(self):
        from dev_workbench.services.review_cleanup import cleanup_reports
        get_all = frappe.get_all
        def scoped(doctype, *args, **kwargs):
            if doctype == api.TASK:
                kwargs.setdefault('filters', {})['name'] = self.task.name
            return get_all(doctype, *args, **kwargs)
        frappe.db.set_value(api.TASK, self.task.name, {'status': 'completed',
            'modified': add_to_date(now_datetime(), days=-100)}, update_modified=False)
        with patch.object(frappe, 'get_all', side_effect=scoped):
            cleanup_reports()
        self.assertFalse(frappe.db.exists(api.TASK, self.task.name))


def run_checks():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewApiTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError('审查集成测试失败')
    return {'tests': result.testsRun, 'passed': True}


def run_http_checks():
    """仅在没有真实排队任务时，用独立合成记录验证 HTTP 机器认证及上传。"""
    import secrets
    import urllib.error
    import urllib.request
    if frappe.db.exists(api.TASK, {'status': ['in', ['queued', 'preparing', 'running']]}):
        return {'skipped': '存在活动任务，不干扰真实队列'}
    original_user = frappe.session.user
    frappe.set_user('Administrator')
    token = secrets.token_urlsafe(48)
    executor = api._insert(api.EXECUTOR, label='synthetic-http', enabled=1, token_hash=api._hash(token))
    task = api._insert(api.TASK, title='synthetic-http-test', status='queued', review_status='pending',
                       head_sha='a' * 40, base_sha='')
    frappe.db.set_value(api.TASK, task.name, 'repository', 'synthetic-http')
    frappe.db.commit()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def call(method, auth=token, **params):
        request = urllib.request.Request('http://127.0.0.1:8000/api/method/dev_workbench.api.v1.code_review.' + method,
            data=json.dumps(params).encode(), headers={'Content-Type': 'application/json', 'X-Review-Token': auth})
        with opener.open(request, timeout=20) as response:
            return json.loads(response.read())['message']
    try:
        with unittest.TestCase().assertRaises(urllib.error.HTTPError):
            call('claim_task', auth='invalid')
        call('report_repositories', repositories={'synthetic-http': 'ready'})
        claim = call('claim_task', tool_version='synthetic-http')
        assert claim['name'] == task.name
        lease = dict(name=task.name, lease_token=claim['lease_token'])
        assert call('heartbeat', **lease)['status'] == 'preparing'
        call('upload_materials', **lease, materials={'head_sha': 'a' * 40, 'base_sha': '',
            'manifest': {'sample.py': {'old': 0, 'new': 1}},
            'files': [{'path': 'new/sample.py', 'content': 'print(1)\n'}],
            'changes': [{'path': 'sample.py', 'diff': '+print(1)', 'old': '', 'new': 'print(1)\n', 'skipped': ''}]})
        call('upload_report', **lease, report={'schema_version': 1, 'summary': '合成接口验证', 'findings': [],
            'coverage': {'reviewed': ['sample.py'], 'skipped': []}, 'limitations': []}, raw_report='synthetic')
        assert frappe.db.get_value(api.TASK, task.name, 'status') == 'completed'
        return {'passed': True, 'checks': ['invalid_token', 'claim', 'heartbeat', 'materials', 'report']}
    finally:
        frappe.db.delete(api.FINDING, {'task': task.name})
        frappe.db.delete(api.ATTEMPT, {'task': task.name})
        frappe.db.delete(api.TASK, {'name': task.name})
        frappe.db.delete(api.EXECUTOR, {'name': executor.name})
        frappe.db.commit()
        frappe.set_user(original_user)
