import unittest

from dev_workbench.services.review_contract import review_key, validate_report


class ReportTests(unittest.TestCase):
    def report(self, **finding):
        return {'schema_version': 1, 'summary': '检查结果', 'findings': [dict(
            severity='high', title='权限缺失', path='api.py', side='new', line=2,
            end_line=2, trigger='非管理员访问', impact='读取私有记录', evidence='返回全部记录',
            suggestion='增加权限校验', uncertainty='', **finding)],
            'coverage': {'reviewed': ['api.py'], 'skipped': []}, 'limitations': []}

    def test_validate_locations_and_coverage(self):
        result = validate_report(self.report(), {'api.py': {'new': 4, 'old': 3}})
        self.assertTrue(result['findings'][0]['located'])
        self.assertFalse(result['partial'])

    def test_unlocatable_line_is_not_a_valid_link(self):
        report = self.report()
        report['findings'][0]['line'] = 200
        self.assertFalse(validate_report(report, {'api.py': {'new': 4}})['findings'][0]['located'])

    def test_escape_paths_are_rejected(self):
        for path in ('../secret', 'C:/secret', '/etc/passwd', 'a\\b'):
            report = self.report()
            report['findings'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_report(report, {'api.py': {'new': 4}})

    def test_empty_or_missing_coverage_is_partial(self):
        report = self.report()
        report['findings'] = []
        report['coverage']['reviewed'] = []
        self.assertTrue(validate_report(report, {'api.py': {'new': 4}})['partial'])

    def test_duplicate_findings_and_bad_severity(self):
        report = self.report()
        report['findings'].append(report['findings'][0].copy())
        self.assertEqual(len(validate_report(report, {'api.py': {'new': 4}})['findings']), 1)
        report['findings'][0]['severity'] = 'critical???'
        with self.assertRaises(ValueError):
            validate_report(report, {})

    def test_key_separates_repository_and_configuration(self):
        self.assertNotEqual(review_key('a', 'b', 'c'), review_key('z', 'b', 'c'))
        self.assertNotEqual(review_key('a', 'b', 'c'), review_key('a', 'b', 'c', 'v2'))


if __name__ == '__main__':
    unittest.main()
