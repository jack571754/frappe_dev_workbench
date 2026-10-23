"""环境面板校验与整形的单元测试（不依赖 frappe）。"""

import unittest

from dev_workbench.services.review_environment import environment_rows, normalize_action, normalize_data_root


class DataRootTests(unittest.TestCase):
    def test_empty_means_default(self):
        self.assertEqual(normalize_data_root(''), '')
        self.assertEqual(normalize_data_root(None), '')
        self.assertEqual(normalize_data_root('   '), '')

    def test_accepts_absolute_paths(self):
        for value in ('C:\\Users\\dev\\AppData\\Local\\DevWorkbench', '/mnt/c/Users/dev/DevWorkbench', '/srv/dev-workbench'):
            self.assertEqual(normalize_data_root('  ' + value + ' '), value)

    def test_rejects_relative_path(self):
        for value in ('DevWorkbench', './data', 'data/root', 'C:relative'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_data_root(value)

    def test_rejects_control_characters_and_overlong(self):
        for value in ('C:\\data\nnext', 'C:\\data\r', 'C:\\data\x00', 'C:\\' + 'a' * 600):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_data_root(value)


class ActionTests(unittest.TestCase):
    def test_known_actions(self):
        self.assertEqual(normalize_action('check'), 'check')
        self.assertEqual(normalize_action('setup'), 'setup')

    def test_rejects_unknown_action(self):
        for value in ('', 'install', 'CHECK', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_action(value)


class RowsTests(unittest.TestCase):
    capabilities = {'repositories': {'sales': 'ready', 'expert': 'unavailable'},
                   'managed_repositories': ['sales']}
    environment = {'repository_paths': {'sales': '/cache/sales.git'}}

    def test_merges_paths_states_and_managed(self):
        rows = environment_rows([('sales', '销售计划'), ('expert', '')], self.capabilities, self.environment)
        self.assertEqual(rows[0], {'name': 'sales', 'repository_name': '销售计划',
                                   'path': '/cache/sales.git', 'readiness': 'ready', 'auto_sync': True})
        self.assertEqual(rows[1], {'name': 'expert', 'repository_name': 'expert',
                                   'path': '', 'readiness': 'unavailable', 'auto_sync': False})

    def test_unknown_repository_is_not_configured(self):
        rows = environment_rows([('other', '其他')], self.capabilities, self.environment)
        self.assertEqual(rows[0]['readiness'], 'not_configured')
        self.assertEqual(rows[0]['path'], '')

    def test_missing_environment_is_tolerated(self):
        rows = environment_rows([('sales', '销售计划')], None, None)
        self.assertEqual(rows[0]['readiness'], 'not_configured')
        self.assertFalse(rows[0]['auto_sync'])

    def test_malformed_payloads_do_not_raise(self):
        rows = environment_rows([('sales', '')], {'repositories': 'bad', 'managed_repositories': 'bad'},
                                {'repository_paths': ['bad']})
        self.assertEqual(rows[0]['readiness'], 'not_configured')


if __name__ == '__main__':
    unittest.main()
