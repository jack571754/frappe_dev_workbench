"""环境面板的输入校验与展示整形；不依赖 Frappe。"""

MAX_DATA_ROOT = 500
ACTIONS = ('check', 'setup')


def normalize_action(mode):
    if mode not in ACTIONS:
        raise ValueError('环境操作无效')
    return mode


def _absolute(text):
    """POSIX 绝对路径、Windows 盘符路径或 UNC 路径。"""
    if text.startswith('/'):
        return True
    if text.startswith('\\\\'):
        return True
    return len(text) > 2 and text[0].isalpha() and text[1] == ':' and text[2] in '\\/'


def normalize_data_root(value):
    """数据目录留空表示使用默认值；非空时必须是绝对路径。"""
    raw = value or ''
    # 换行/回车/空字节必须在去空白之前拦掉，否则会被 strip 掩盖。
    if any(character in raw for character in '\r\n\0'):
        raise ValueError('数据目录无效')
    text = raw.strip()
    if len(text) > MAX_DATA_ROOT:
        raise ValueError('数据目录无效')
    if text and not _absolute(text):
        raise ValueError('请填写绝对路径，例如 C:\\Users\\<用户名>\\AppData\\Local\\DevWorkbench')
    return text


def environment_rows(repositories, capabilities, environment):
    """把执行端上报的能力与环境合并成面板行；缺失字段一律按未配置处理。"""
    capabilities = capabilities if isinstance(capabilities, dict) else {}
    paths, states, managed = {}, {}, []
    if isinstance(environment, dict) and isinstance(environment.get('repository_paths'), dict):
        paths = {str(key): str(value) for key, value in environment['repository_paths'].items()}
    if isinstance(capabilities.get('repositories'), dict):
        states = capabilities['repositories']
    if isinstance(capabilities.get('managed_repositories'), list):
        managed = capabilities['managed_repositories']
    return [{'name': name, 'repository_name': display or name, 'path': paths.get(name, ''),
             'readiness': states.get(name, 'not_configured'), 'auto_sync': name in managed}
            for name, display in repositories]
