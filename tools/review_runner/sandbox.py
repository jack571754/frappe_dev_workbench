"""Docker 提供系统级隔离，CLI 只允许文件读取。执行器在本机 WSL 运行。"""

from pathlib import Path, PurePosixPath
from local_provider import PROVIDER_KEYS


def command(snapshot, name, image='dev-workbench-review:2.1.306'):
    return ['docker', 'run', '--rm', '-i', '--name', name, '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=128',
            '--memory=2g', '--cpus=2', '--user=1000:1000',
            '--mount', f'type=bind,source={snapshot},target=/review,readonly',
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m,mode=1777',
            '--workdir=/review', '-e', 'HOME=/tmp/home',
            *[arg for key in (*PROVIDER_KEYS, 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC') for arg in ('-e', key)],
            image, 'claude', '--print', '--restricted', '--safe-mode',
            '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
            '--tools', 'Read,Glob,Grep', '--allowedTools', 'Read,Glob,Grep',
            '--permission-mode', 'dontAsk', '--no-session-persistence',
            '--output-format', 'json']


def write_materials(root, materials):
    root = Path(root).resolve()
    for item in materials.get('files', []):
        path = item['path']
        if (not path or path.startswith('/') or '\\' in path or ':' in path or
                any(p in ('', '.', '..', '.git') for p in path.split('/'))):
            raise ValueError('非法材料路径')
        dest = root.joinpath(*PurePosixPath(path).parts)
        if dest.is_symlink() or not dest.resolve().is_relative_to(root):
            raise ValueError('材料路径越界')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(item['content'], encoding='utf-8')
