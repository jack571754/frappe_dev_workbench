"""执行端环境自检与一键配置：只读检查本机是否具备审查条件，结论回传工作台。"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import paths


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _check(name, label, passed, detail=''):
    return {'check': name, 'label': label, 'passed': bool(passed), 'detail': str(detail)[:300]}


def _run(arguments, timeout=20):
    try:
        return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def _first_line(arguments, timeout=20):
    result = _run(arguments, timeout)
    if not result or result.returncode != 0:
        return ''
    lines = ((result.stdout or '') + (result.stderr or '')).strip().splitlines()
    return lines[0].strip() if lines else ''


def _image_exists(name):
    result = _run(['docker', 'image', 'inspect', name])
    return bool(result and result.returncode == 0)


def _writable(root):
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        probe = root / '.write-probe'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink()
        return True
    except OSError:
        return False


def _free_gb(root):
    try:
        return round(shutil.disk_usage(str(root)).free / (1024 ** 3), 1)
    except OSError:
        return 0.0


def collect(config, root=None):
    """采集一次环境状态；不修改任何配置，结果结构直接给工作台展示。"""
    base = Path(root) if root else paths.data_root(config.get('data_root', ''))
    git = _first_line(['git', '--version'])
    docker = _first_line(['docker', '--version'])
    checks = [
        _check('python', 'Python', sys.version_info >= (3, 9), sys.version.split()[0] + ' / ' + sys.platform),
        _check('git', 'Git', bool(git), git or '未找到 git，无法读取或下载仓库'),
        _check('docker', 'Docker', bool(docker), docker or '未找到 docker，无法运行隔离审查'),
    ]
    image = config.get('image', 'dev-workbench-review:2.1.306')
    checks.append(_check('review_image', '审查镜像', _image_exists(image), image))
    if config.get('engine', 'open-code-review') == 'open-code-review':
        ocr_image = config.get('ocr_image', 'dev-workbench-ocr:1.13.2')
        checks.append(_check('ocr_image', 'OpenCodeReview 镜像', _image_exists(ocr_image), ocr_image))
    writable = _writable(base)
    checks.append(_check('data_root', '数据目录', writable,
                         str(base) + ('（剩余 ' + str(_free_gb(base)) + ' GB）' if writable else '（不可写）')))
    target = paths.config_path(base)
    checks.append(_check('config', '执行端配置', target.is_file(), str(target)))
    models = config.get('claude_settings_file') or ''
    if models:
        from local_provider import load_provider, ProviderConfigurationError
        try:
            if config.get('engine', 'open-code-review') == 'open-code-review':
                from ocr_engine import provider_environment
                provider_environment(config)
            else:
                load_provider(models)
            checks.append(_check('model_settings', '模型配置', True, 'JSON、第三方地址、凭证和模型配置有效（未验证接口连通性）'))
        except ProviderConfigurationError as error:
            checks.append(_check('model_settings', '模型配置', False, str(error)))
    else:
        checks.append(_check('model_settings', '模型配置', False, '未设置本机模型配置文件'))
    return {
        'platform': sys.platform,
        'data_root': str(base),
        'legacy_data_root': str(paths.LEGACY_ROOT),
        'checks': checks,
        'ready': all(item['passed'] for item in checks),
        'repository_paths': {str(name): str(value) for name, value in (config.get('repositories') or {}).items()},
        'reported_at': _now(),
    }


def setup(config, root=None):
    """一键配置：建数据目录、迁移旧 .local、给出每一项的结果。"""
    base = Path(root) if root else paths.data_root(config.get('data_root', ''))
    created = _writable(base)
    steps = [_check('data_root', '准备数据目录', created, str(base))]
    moved = paths.migrate(base)
    steps.append(_check('migrate', '迁移旧数据', True,
                        ('已迁移：' + '、'.join(moved)) if moved else '无需迁移'))
    config_target = paths.config_path(base)
    steps.append(_check('config', '执行端配置', config_target.is_file(),
                        str(config_target) if config_target.is_file() else '当前配置仍在旧位置，重启执行端后生效'))
    return {'data_root': str(base), 'steps': steps}
