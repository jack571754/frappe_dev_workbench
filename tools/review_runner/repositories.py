"""本机仓库检查与路径配置；不运行仓库代码，不上传本地路径。"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from local_provider import settings_path


def git_environment():
    # 不继承开发者的 Git 对象目录、工作区、TRACE 或命令配置，避免写出审查缓存及记录认证信息。
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update({'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/bin/false',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'})
    return env


def check_repositories(mapping):
    result = {}
    for name, value in mapping.items():
        result[name] = 'unavailable'
        try:
            path = settings_path(value).resolve()
            if not path.is_dir():
                continue
            check = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(path),
                                    'rev-parse', '--is-bare-repository'], capture_output=True, timeout=5, env=git_environment())
            if check.returncode == 0:
                root_flag = '--absolute-git-dir' if check.stdout.strip() == b'true' else '--show-toplevel'
                root = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(path),
                                       'rev-parse', root_flag], capture_output=True, timeout=5, env=git_environment())
                if root.returncode == 0 and Path(os.fsdecode(root.stdout).strip()).resolve() == path:
                    result[name] = 'ready'
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    return result


def configure(config_path, repository, path):
    if not repository or len(repository) > 140:
        raise ValueError('仓库名称无效')
    path = str(settings_path(path).resolve())
    if check_repositories({repository: path})[repository] != 'ready':
        raise ValueError('目录不存在、不可读或不是 Git 仓库；请先克隆仓库再配置')
    config_path = Path(config_path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    config.setdefault('repositories', {})[repository] = path
    fd, temporary = tempfile.mkstemp(dir=config_path.parent, prefix='.repository-config-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, config_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='./.local/config.json')
    parser.add_argument('--repository', required=True)
    parser.add_argument('--path', required=True)
    args = parser.parse_args()
    try:
        configure(args.config, args.repository, args.path)
    except (OSError, ValueError):
        raise SystemExit('配置失败：请确认配置文件存在，且路径是可读的 Git 仓库。')
    print('仓库路径已保存并通过检查；运行中的新版执行端将在下一轮自动加载。')
