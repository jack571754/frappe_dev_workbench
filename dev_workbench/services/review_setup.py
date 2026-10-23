"""只供 bench 本地配置使用，机器令牌写文件，不返回到终端。"""

import json
import os
from pathlib import Path

import frappe


def provision_local():
    if getattr(frappe.local, 'request', None):
        frappe.throw('此操作只允许在服务器命令行执行', frappe.PermissionError)
    from dev_workbench.api.v1.code_review import register_executor
    app = Path(__file__).resolve().parents[2]
    # 冷启动配置先写在这里；执行端第一次启动会把整个 .local 迁移到数据目录
    # （默认 %LOCALAPPDATA%\DevWorkbench），项目目录里不再保留下载内容。
    directory = app / 'tools' / 'review_runner' / '.local'
    directory.mkdir(exist_ok=True, mode=0o700)
    target = directory / 'config.json'
    if target.exists():
        return {'configured': True, 'created': False}
    executor = register_executor('当前 Windows 电脑 / WSL Docker')
    # 容器工作区为当前 Windows 工作区的 bind mount；运行器在 WSL 主机执行。
    host_root = '/mnt/d/project/02-开源项目/frappe_docker/development/frappe-bench/apps'
    repositories = {}
    for row in frappe.get_all('Codeup Repository', filters={'is_active': 1}, fields=['name']):
        candidate = app.parent / row.name
        if candidate.is_dir() and (candidate / '.git').exists():
            repositories[row.name] = host_root + '/' + row.name
    config = {'url': 'http://127.0.0.1:8000', 'token': executor['token'], 'engine': 'open-code-review',
        'executor': executor['name'], 'image': 'dev-workbench-review:2.1.306',
        'repositories': repositories, 'timeout_seconds': 1200, 'poll_seconds': 10}
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
    frappe.db.commit()
    return {'configured': True, 'created': True, 'repositories': list(repositories)}
