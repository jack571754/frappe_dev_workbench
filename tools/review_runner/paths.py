"""执行端数据目录：配置、下载缓存和快照默认放在 %LOCALAPPDATA%\\DevWorkbench。

这样项目目录里不再保存任何下载内容；旧版本的 ``tools/review_runner/.local``
会在第一次启动时自动迁移，迁移后可以整个删掉。
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = TOOL_ROOT / '.local'
DEFAULT_NAME = 'DevWorkbench'
LEGACY_FALLBACK = '.dev-workbench'
MIGRATED = ('config.json', 'managed-repositories', 'repositories', 'ui-preview', 'logs',
            'check_scan.py', 'ui_smoke.py', 'dev-services.Procfile')


def _is_wsl():
    if sys.platform != 'linux':
        return False
    try:
        return 'microsoft' in Path('/proc/version').read_text(encoding='utf-8', errors='ignore').lower()
    except OSError:
        return False


def windows_to_posix(value):
    """``C:\\Users\\...`` → ``/mnt/c/Users/...``；不是盘符路径时返回 None。"""
    text = (value or '').strip().replace('\r', '')
    if len(text) < 3 or text[1] != ':':
        return None
    drive, rest = text[0].lower(), text[2:].lstrip('\\/').replace('\\', '/')
    return '/mnt/' + drive + '/' + rest if rest else '/mnt/' + drive


def posix_to_windows(value):
    """``/mnt/c/Users/...`` → ``C:\\Users\\...``；不是 WSL 挂载路径时返回 None。"""
    text = (value or '').strip()
    match = re.fullmatch(r'/mnt/([A-Za-z])(?:/(.*))?', text)
    if not match:
        return None
    drive, rest = match.group(1).upper(), (match.group(2) or '').replace('/', '\\')
    return drive + ':\\' + rest if rest else drive + ':\\'


def _windows_path(value):
    """把 Windows 路径转成当前平台可用的路径（WSL 下转 /mnt/x）。"""
    converted = windows_to_posix(value)
    if converted is None:
        return None
    return Path(converted)


def normalize_path(value):
    """网页上填的路径可能是另一套系统的写法，按当前平台互转。"""
    text = (value or '').strip()
    if not text:
        return text
    if sys.platform == 'win32':
        return posix_to_windows(text) or text
    return windows_to_posix(text) or text


def _windows_local_appdata():
    value = os.environ.get('LOCALAPPDATA')
    if sys.platform == 'win32':
        return Path(value) if value else Path.home() / 'AppData' / 'Local'
    if not _is_wsl():
        return None
    try:
        result = subprocess.run(['cmd.exe', '/c', 'echo %LOCALAPPDATA%'],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return _windows_path(result.stdout)


def data_root(override=''):
    """数据目录：显式参数 > DEV_WORKBENCH_HOME > Windows %LOCALAPPDATA%\\DevWorkbench > ~/.dev-workbench。"""
    value = (override or os.environ.get('DEV_WORKBENCH_HOME') or '').strip()
    if value:
        return Path(normalize_path(value)).expanduser()
    windows = _windows_local_appdata()
    if windows is not None:
        return windows / DEFAULT_NAME
    return Path.home() / LEGACY_FALLBACK


def config_path(root=None, name='config.json'):
    return (Path(root) if root else data_root()) / name


def legacy_config_path():
    return LEGACY_ROOT / 'config.json'


def migrate(root=None):
    """把旧版 ``.local`` 下的配置与缓存搬到数据目录，返回实际迁移的条目。"""
    target = Path(root) if root else data_root()
    try:
        if target.resolve() == LEGACY_ROOT.resolve():
            return []
    except OSError:
        pass
    if not LEGACY_ROOT.is_dir():
        return []
    moved = []
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in MIGRATED:
        source, destination = LEGACY_ROOT / name, target / name
        if not source.exists() or destination.exists():
            continue
        try:
            shutil.move(str(source), str(destination))
        except (OSError, shutil.Error):
            continue
        moved.append(name)
    return moved
