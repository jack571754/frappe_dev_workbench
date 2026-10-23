"""不依赖 Frappe 的审查输出契约。"""

import copy
import hashlib
import json
import re
from pathlib import PurePosixPath

RULES_VERSION = 'readonly-v2-open-code-review'
SEVERITIES = ('high', 'medium', 'low', 'suggestion')


def safe_path(path):
    if not isinstance(path, str) or not path or len(path) > 1024:
        raise ValueError('文件路径无效')
    parts = PurePosixPath(path).parts
    if path.startswith('/') or '\\' in path or ':' in path or '\x00' in path:
        raise ValueError('禁止绝对路径或特殊路径')
    if any(p in ('.', '..', '.git') for p in path.split('/')) or not parts:
        raise ValueError('禁止路径穿越或 Git 配置')
    return path


def review_key(repository, base_sha, head_sha, rules_version=RULES_VERSION, config_version='1'):
    return hashlib.sha256(json.dumps([repository, base_sha, head_sha, rules_version,
                                      config_version], ensure_ascii=False).encode()).hexdigest()


def validate_sha(sha):
    if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha):
        raise ValueError('需要完整提交 SHA')
    return sha


def text(value, limit=6000):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError('报告字段类型或长度无效')
    return value


def validate_report(report, manifest):
    if not isinstance(report, dict) or report.get('schema_version') != 1:
        raise ValueError('报告版本无效')
    summary = text(report.get('summary'))
    findings = report.get('findings')
    coverage = report.get('coverage')
    limitations = report.get('limitations')
    if not isinstance(findings, list) or len(findings) > 200 or not isinstance(coverage, dict):
        raise ValueError('报告结构无效')
    if not isinstance(limitations, list) or len(limitations) > 100:
        raise ValueError('覆盖说明无效')
    limitations = [text(v) for v in limitations]
    reviewed, skipped = coverage.get('reviewed'), coverage.get('skipped')
    if not isinstance(reviewed, list) or not isinstance(skipped, list):
        raise ValueError('缺少覆盖范围')
    for path in reviewed:
        safe_path(path)
        if path not in manifest or manifest[path].get('skipped'):
            raise ValueError('报告声明了未提供的文件')
    for item in skipped:
        if not isinstance(item, dict):
            raise ValueError('跳过文件需说明原因')
        safe_path(item.get('path'))
        text(item.get('reason'))
    cleaned, seen = [], set()
    for finding in findings:
        if not isinstance(finding, dict) or finding.get('severity') not in SEVERITIES:
            raise ValueError('问题严重程度无效')
        item = {key: text(finding.get(key, '')) for key in (
            'title', 'path', 'trigger', 'impact', 'evidence', 'suggestion', 'uncertainty')}
        safe_path(item['path'])
        if not item['title'] or not item['evidence']:
            raise ValueError('问题缺少标题或依据')
        side = finding.get('side')
        if side not in ('old', 'new'):
            raise ValueError('代码侧无效')
        line, end = finding.get('line'), finding.get('end_line')
        valid_int = lambda n: isinstance(n, int) and not isinstance(n, bool)
        count = manifest.get(item['path'], {}).get(side, 0)
        located = valid_int(line) and valid_int(end) and 1 <= line <= end <= count
        item.update(severity=finding['severity'], side=side, line=line if located else 0,
                    end_line=end if located else 0, located=bool(located))
        identity = (item['path'], side, item['line'], item['title'])
        if identity not in seen:
            cleaned.append(item)
            seen.add(identity)
    partial = bool(skipped or limitations or not manifest or
                   set(reviewed) != set(manifest) or any(v.get('skipped') for v in manifest.values()))
    return dict(schema_version=1, summary=summary, findings=cleaned, coverage=copy.deepcopy(coverage),
                limitations=limitations, partial=partial)


REPORT_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['schema_version', 'summary', 'findings', 'coverage', 'limitations'],
    'properties': {
        'schema_version': {'type': 'integer', 'const': 1},
        'summary': {'type': 'string'},
        'findings': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['severity', 'title', 'path', 'side', 'line', 'end_line', 'trigger',
                         'impact', 'evidence', 'suggestion', 'uncertainty'],
            'properties': {
                **{k: {'type': 'string'} for k in ('title', 'path', 'trigger', 'impact', 'evidence',
                                                   'suggestion', 'uncertainty')},
                'severity': {'type': 'string', 'enum': list(SEVERITIES)},
                'side': {'type': 'string', 'enum': ['old', 'new']},
                'line': {'type': 'integer'}, 'end_line': {'type': 'integer'},
            }}},
        'coverage': {'type': 'object', 'additionalProperties': False,
                     'required': ['reviewed', 'skipped'], 'properties': {
                         'reviewed': {'type': 'array', 'items': {'type': 'string'}},
                         'skipped': {'type': 'array', 'items': {'type': 'object',
                             'additionalProperties': False, 'required': ['path', 'reason'],
                             'properties': {'path': {'type': 'string'}, 'reason': {'type': 'string'}}}}}},
        'limitations': {'type': 'array', 'items': {'type': 'string'}},
    },
}
