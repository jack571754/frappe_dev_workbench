"""只下载到独立审查缓存；不 checkout，不保存 Git 凭证，不操作开发目录。"""
import base64
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

from processes import run_process
from repositories import configure, git_environment as _git_environment
from local_provider import settings_path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dev_workbench.services.review_repository_source import validate_source_url


def _target(config_path, repository):
    root = Path(config_path).expanduser().resolve().parent / 'managed-repositories'
    if root.is_symlink():
        raise ValueError('审查缓存目录不能是链接')
    digest = hashlib.sha256(repository.encode('utf-8')).hexdigest()
    target = root / (digest + '.git')
    if target.is_symlink():
        raise ValueError('审查缓存不能是链接')
    return target, digest


def is_managed(config_path, repository, path):
    if config_path is None or not path:
        return False
    try:
        target, digest = _target(config_path, repository)
        return (settings_path(path).resolve() == target and
                (target / '.review-managed').read_text(encoding='utf-8') == digest)
    except (OSError, ValueError):
        return False


def _git(target, args, heartbeat, env=None):
    return run_process(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
        '-c', 'http.followRedirects=false', '-c', 'http.sslVerify=true', '-c', 'maintenance.auto=false',
        '-c', 'gc.auto=0', '-C', str(target), *args],
        heartbeat, env=env if env is not None else _git_environment())


def _fetch(target, source, refs, heartbeat):
    url = validate_source_url(source['url'])
    token = source['access_token']
    if not isinstance(token, str) or not token or len(token) > 8192:
        raise ValueError('仓库凭证无效')
    env = _git_environment()
    env.update({'GIT_CONFIG_COUNT': '2',
        'GIT_CONFIG_KEY_0': 'credential.helper', 'GIT_CONFIG_VALUE_0': '',
        'GIT_CONFIG_KEY_1': 'http.extraHeader', 'GIT_CONFIG_VALUE_1': 'Authorization: Basic ' +
        base64.b64encode(('oauth2:' + token).encode()).decode()})
    # 同一轮拉取全部目标 SHA，避免逐个浅拉取将其他目标标成 shallow 边界。
    _git(target, ['fetch', '--no-tags', '--no-recurse-submodules', '--depth=20', url, *refs], heartbeat, env)
    for ref in refs:
        sha = _git(target, ['rev-parse', 'FETCH_HEAD'], heartbeat).strip() if ref == 'HEAD' else ref
        _git(target, ['cat-file', '-e', sha + '^{commit}'], heartbeat)
        _git(target, ['update-ref', 'refs/review/' + ('default' if ref == 'HEAD' else sha), sha], heartbeat)


def prepare(config_path, repository, source, heartbeat):
    validate_source_url(source['url'])
    target, digest = _target(config_path, repository)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not target.exists():
        with tempfile.TemporaryDirectory(prefix='.prepare-', dir=target.parent) as temporary:
            run_process(['git', '-c', 'core.hooksPath=/dev/null', 'init', '--bare', '--template=', temporary],
                        heartbeat, env=_git_environment())
            Path(temporary, '.review-managed').write_text(digest, encoding='utf-8')
            os.rename(temporary, target)
    if not is_managed(config_path, repository, str(target)):
        raise ValueError('目标目录不是自动管理的审查缓存')
    _fetch(target, source, ['HEAD'], heartbeat)
    configure(config_path, repository, str(target))
    return target


def sync(config_path, repository, source, shas, heartbeat):
    target, _ = _target(config_path, repository)
    if not is_managed(config_path, repository, str(target)):
        raise ValueError('只允许同步专用审查缓存')
    shas = list(dict.fromkeys(sha for sha in shas if sha))
    if not shas or any(not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha) for sha in shas):
        raise ValueError('待同步提交无效')
    _fetch(target, source, shas, heartbeat)
    return target
