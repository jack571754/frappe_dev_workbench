"""仅复用本机 Claude CLI 的第三方模型配置，不加载钩子或开发权限。"""

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

PROVIDER_KEYS = (
    'ANTHROPIC_BASE_URL', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL',
    'ANTHROPIC_DEFAULT_OPUS_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL',
    'ANTHROPIC_DEFAULT_HAIKU_MODEL', 'ANTHROPIC_SMALL_FAST_MODEL',
    'ANTHROPIC_DEFAULT_OPUS_MODEL_NAME', 'ANTHROPIC_DEFAULT_SONNET_MODEL_NAME',
    'ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME', 'CLAUDE_CODE_SUBAGENT_MODEL',
    'ANTHROPIC_DEFAULT_FABLE_MODEL', 'ANTHROPIC_DEFAULT_FABLE_MODEL_NAME',
)


class ProviderConfigurationError(ValueError):
    """Safe configuration diagnostics; never include source text or credentials."""


def settings_path(value):
    value = str(value).replace('\\', '/')
    if re.match(r'^[a-zA-Z]:/', value):
        value = '/mnt/' + value[0].lower() + value[2:]
    return Path(value).expanduser()


def load_provider(settings_file):
    path = Path(settings_file).expanduser() if os.name == 'nt' else settings_path(settings_file)
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as error:
        raise ProviderConfigurationError(
            f'本机模型配置 JSON 格式错误：第 {error.lineno} 行，第 {error.colno} 列；请检查 Claude settings.json') from None
    except (OSError, UnicodeError):
        raise ProviderConfigurationError('本机模型配置无法读取，请检查 Claude settings.json 文件及权限') from None
    if not isinstance(data, dict) or not isinstance(data.get('env', {}), dict):
        raise ProviderConfigurationError('本机模型配置及 env 必须是 JSON 对象')
    source = data.get('env', {})
    result = {key: str(source[key]) for key in PROVIDER_KEYS if source.get(key)}
    if data.get('model'):
        result['ANTHROPIC_MODEL'] = str(data['model'])
    endpoint = urlparse(result.get('ANTHROPIC_BASE_URL', ''))
    if endpoint.scheme not in ('https', 'http') or not endpoint.hostname:
        raise ProviderConfigurationError('本机 Claude 配置缺少有效的第三方模型地址')
    if not (result.get('ANTHROPIC_AUTH_TOKEN') or result.get('ANTHROPIC_API_KEY')):
        raise ProviderConfigurationError('本机 Claude 配置缺少第三方模型凭证')
    result['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings-file', required=True)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    source = settings_path(args.settings_file).resolve()
    provider = load_provider(source)
    target = Path(args.config).resolve()
    config = json.loads(target.read_text(encoding='utf-8-sig'))
    config['claude_settings_file'] = str(source)
    config.pop('credentials_file', None)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Local Claude CLI third-party provider configured. No official login required; credentials not copied.')
