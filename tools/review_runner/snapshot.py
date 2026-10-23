"""从明确配置的本机 Git 仓库读取提交对象，不 checkout/fetch 或执行仓库脚本。"""

import difflib
import re
import subprocess
from pathlib import Path

MAX_FILE = 160_000
MAX_TOTAL = 2_000_000
MAX_CHANGED = 200


def git(repository, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
        '-c', 'core.fsmonitor=false', '--no-pager', '-C', str(repository), *args],
        timeout=30, stderr=subprocess.DEVNULL)


def _path(path):
    if (not path or path.startswith('/') or '\\' in path or ':' in path or '\x00' in path or
            any(p in ('', '.', '..', '.git') for p in path.split('/'))):
        raise ValueError('非法 Git 路径')
    return path


def _sensitive(path):
    name = Path(path).name.lower()
    return (name == '.env' or name.startswith('.env.') or name in
            ('site_config.json', 'common_site_config.json', '.credentials.json', '.npmrc') or
            name.endswith(('.pem', '.key', '.p12', '.pfx')))


def prepare_materials(repository, base_sha, head_sha):
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', head_sha):
        raise ValueError('无效 SHA')
    if base_sha and not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', base_sha):
        raise ValueError('无效父提交')
    parents = git(repository, 'rev-list', '--parents', '-n', '1', head_sha).decode().split()
    if parents[1:] != ([base_sha] if base_sha else []):
        raise ValueError('版本范围不匹配或合并提交不受支持')
    # 根提交直接比较空树；hash-object 不使用 -w，不写入对象库。
    base = base_sha or subprocess.check_output(['git', '-C', str(repository), 'hash-object',
        '-t', 'tree', '--stdin'], input=b'', timeout=30).decode().strip()
    changed = git(repository, 'diff', '--no-ext-diff', '--no-renames', '--name-only', '-z', base, head_sha).decode('utf-8').split('\0')
    changed = [_path(p) for p in changed if p]
    if len(changed) > MAX_CHANGED:
        raise ValueError('提交包含超过 200 个文件，请拆分提交后审查')
    tree = {}
    for sha, side in ((base_sha, 'old'), (head_sha, 'new')):
        tree[side] = {}
        if not sha:
            continue
        entries = git(repository, 'ls-tree', '-rz', '-l', sha).decode('utf-8').split('\0')
        for entry in entries:
            if not entry:
                continue
            meta, path = entry.split('\t', 1)
            mode, kind, oid, size = meta.split()
            tree[side][path] = (mode, kind, oid, int(size) if size.isdigit() else 0)
    files, changes, manifest, used = [], [], {}, 0
    for path in changed:
        info, contents, reason = {'old': 0, 'new': 0,
            'old_exists': path in tree['old'], 'new_exists': path in tree['new']}, {}, ''
        for side, sha in (('old', base_sha), ('new', head_sha)):
            entry = tree[side].get(path)
            if not entry:
                contents[side] = ''
                continue
            mode, kind, oid, size = entry
            info[side + '_mode'] = mode
            if _sensitive(path) or mode not in ('100644', '100755') or kind != 'blob':
                reason = '敏感配置、符号链接或子仓库不发送给模型'
                continue
            if size > MAX_FILE or used + size > MAX_TOTAL:
                reason = '文件或任务超过读取上限'
                continue
            data = git(repository, 'cat-file', 'blob', oid)
            try:
                if b'\0' in data:
                    raise UnicodeError()
                content = data.decode('utf-8')
            except UnicodeError:
                reason = '二进制或非 UTF-8 文件'
                continue
            used += len(data)
            info[side] = len(content.splitlines())
            contents[side] = content
        if reason:
            info['skipped'] = reason
            diff = ''
        else:
            diff = ''.join(difflib.unified_diff(contents['old'].splitlines(keepends=True),
                contents['new'].splitlines(keepends=True), fromfile='a/' + path, tofile='b/' + path))
            for side in ('old', 'new'):
                files.append({'path': side + '/' + path, 'content': contents.get(side, '')})
        manifest[path] = info
        changes.append({'path': path, 'diff': diff, 'old': contents.get('old', '') if not reason else '',
                        'new': contents.get('new', '') if not reason else '', 'skipped': reason})
    # 有限读取同版本其他源码作为调用上下文，覆盖清单仍只统计变更文件。
    context_count = 0
    for path, entry in sorted(tree['new'].items()):
        mode, kind, oid, size = entry
        if (path in changed or _sensitive(path) or mode not in ('100644', '100755') or
                kind != 'blob' or size > MAX_FILE or used + size > MAX_TOTAL or context_count >= 200):
            continue
        if Path(path).suffix.lower() not in ('.py', '.vue', '.js', '.ts', '.json', '.sql', '.go', '.java'):
            continue
        _path(path)
        data = git(repository, 'cat-file', 'blob', oid)
        try:
            content = data.decode('utf-8')
            if '\0' in content:
                continue
        except UnicodeError:
            continue
        files.append({'path': 'context/' + path, 'content': content})
        used += len(data)
        context_count += 1
    return {'head_sha': head_sha, 'base_sha': base_sha, 'manifest': manifest, 'files': files,
            'changes': changes, 'context_note': '仅附带部分相关版本源码；不能读取材料目录外文件。未提供的调用方请注明假设。'}


SCAN_EXCLUDED = {'node_modules', 'vendor', 'dist', 'build', '__pycache__', 'venv', '.venv', 'coverage'}


def prepare_scan_materials(repository, head_sha):
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', head_sha):
        raise ValueError('无效 SHA')
    # 只读取固定提交树，不读取工作目录，也不执行项目配置。
    entries = git(repository, 'ls-tree', '-rz', '-l', head_sha).decode('utf-8').split('\0')
    manifest, changes, used = {}, [], 0
    for entry in entries:
        if not entry:
            continue
        meta, path = entry.split('\t', 1)
        _path(path)
        mode, kind, oid, size = meta.split()
        size = int(size) if size.isdigit() else 0
        reason, content = '', ''
        if _sensitive(path) or any(p.startswith('.') or p in SCAN_EXCLUDED for p in path.split('/')):
            reason = '敏感配置、隐藏配置或生成目录不进入扫描'
        elif mode not in ('100644', '100755') or kind != 'blob':
            reason = '符号链接或子仓库不进入扫描'
        elif size > 500_000 or used + size > 20_000_000:
            reason = '超过单文件 500KB 或任务 20MB 材料上限'
        else:
            data = git(repository, 'cat-file', 'blob', oid)
            try:
                if b'\0' in data:
                    raise UnicodeError()
                content = data.decode('utf-8')
                used += len(data)
            except UnicodeError:
                reason = '二进制或非 UTF-8 文件'
        info = {'old': 0, 'new': len(content.splitlines()), 'old_exists': False,
                'new_exists': True, 'new_mode': mode}
        if reason:
            info['skipped'] = reason
        manifest[path] = info
        changes.append({'path': path, 'old': '', 'new': content, 'diff': '', 'skipped': reason})
        if len(manifest) > 10000:
            raise ValueError('项目超过 10000 个文件，请拆分仓库后扫描')
    return {'mode': 'scan', 'head_sha': head_sha, 'base_sha': '', 'manifest': manifest,
            'changes': changes, 'files': [], 'context_note': '固定提交的完整文件扫描；跳过内容已列明。'}


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', required=True)
    parser.add_argument('--base', default='')
    parser.add_argument('--head', required=True)
    parser.add_argument('--mode', choices=['commit', 'scan'], default='commit')
    args = parser.parse_args()
    print(json.dumps(prepare_scan_materials(args.repository, args.head) if args.mode == 'scan' else
                     prepare_materials(args.repository, args.base, args.head), ensure_ascii=False))
