"""仅使用合成代码验证 Docker 和 Claude Code；不访问成员代码。"""

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from sandbox import command
from local_provider import load_provider


def probe_evidence(output):
    """只信任 CLI 的真实工具调用/结果事件，不采信模型关于权限的自述。"""
    calls, sample_read, outside_denied = {}, False, False
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        message = event.get('message')
        if not isinstance(message, dict):
            continue
        blocks = message.get('content', [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if event.get('type') == 'assistant' and block.get('type') == 'tool_use' and block.get('name') == 'Read':
                calls[block['id']] = block.get('input', {}).get('file_path')
            if event.get('type') == 'user' and block.get('type') == 'tool_result':
                path = calls.get(block.get('tool_use_id'))
                content = block.get('content', '')
                if isinstance(content, list):
                    content = '\n'.join(b.get('text', '') for b in content if isinstance(b, dict))
                if path == '/review/sample.py' and not block.get('is_error') and 'def divide(a, b)' in content:
                    sample_read = True
                if path == '/etc/hostname' and block.get('is_error') is True:
                    outside_denied = True
    return sample_read and outside_denied


def model_environment(settings_file=None):
    # 不继承工作台、仓库及用户其他环境变量。
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'DOCKER_HOST', 'XDG_RUNTIME_DIR') if k in os.environ}
    if settings_file:
        env.update(load_provider(settings_file))
    return env


def preflight(config, model_probe=True):
    image = config.get('image', 'dev-workbench-review:2.1.306')
    checks = []
    container_name = 'review-probe-' + uuid.uuid4().hex[:12]
    try:
        with tempfile.TemporaryDirectory(prefix='review-preflight-') as root:
            os.chmod(root, 0o755)
            Path(root, 'sample.py').write_text('def divide(a, b):\n    return a / b\n', encoding='utf-8')
            args = command(root, container_name, image)
            # 使用同一隔离参数，真实尝试写入只读挂载和读取宿主路径。
            index = args.index(image)
            probe = args[:index + 1] + ['python', '-c',
                "from pathlib import Path; import os; "
                "p=Path('/review/sample.py'); assert p.exists(); "
                "assert not Path('/var/run/docker.sock').exists(); "
                "assert not Path('/mnt/c/Users').exists(); "
                "exec(\"try:\\n p.write_text('changed')\\n raise AssertionError('write allowed')\\nexcept OSError:\\n pass\"); "
                "assert p.read_text().startswith('def divide'); print('isolated')"]
            process = subprocess.run(probe, text=True, capture_output=True, timeout=45,
                                     env=model_environment())
            isolated = process.returncode == 0 and 'isolated' in process.stdout
            checks.append({'check': 'readonly_container', 'passed': isolated})
            if not isolated:
                return {'ready': False, 'checks': checks}
            if model_probe:
                prompt = ('This is a synthetic preflight. Read /review/sample.py. '
                          'Try reading /etc/hostname using Read (it must be rejected outside the working directory). '
                          'Do not modify files. Reply only PREFLIGHT_OK after reading sample.py, and mention '
                          'whether outside reading was denied. Do not execute commands.')
                args[args.index('--output-format') + 1] = 'stream-json'
                args.append('--verbose')
                process = subprocess.run(args, input=prompt, text=True, capture_output=True,
                    timeout=120, env=model_environment(config['claude_settings_file']))
                ok = process.returncode == 0 and probe_evidence(process.stdout)
                checks.append({'check': 'authenticated_read_and_outside_denial', 'passed': ok})
            return {'ready': all(v['passed'] for v in checks), 'checks': checks}
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        checks.append({'check': 'runtime_available', 'passed': False})
        return {'ready': False, 'checks': checks}
    finally:
        try:
            subprocess.run(['docker', 'rm', '-f', container_name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=20)
        except (OSError, subprocess.SubprocessError):
            pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings-file')
    parser.add_argument('--config')
    parser.add_argument('--isolation-only', action='store_true')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8')) if args.config else {}
    if args.settings_file:
        config['claude_settings_file'] = args.settings_file
    result = preflight(config, not args.isolation_only)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['ready'] else 1)
