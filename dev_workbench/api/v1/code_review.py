"""管理者与本机执行器的独立审查接口；所有仓库操作均为读取。"""

import hashlib
import hmac
import json
import secrets

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from dev_workbench.permissions import require_manager
from dev_workbench.services.review_contract import review_key, safe_path, validate_report, validate_sha
from dev_workbench.services.review_environment import environment_rows, normalize_action, normalize_data_root

TASK = 'Code Review Task'
ATTEMPT = 'Code Review Attempt'
FINDING = 'Code Review Finding'
EXECUTOR = 'Code Review Executor'
PREPARATION = 'Code Review Repository Preparation'
ACTIVE = ('preparing', 'running')


def _fresh_capabilities(executor):
    if not executor.capabilities_at or not 0 <= (now_datetime() - get_datetime(executor.capabilities_at)).total_seconds() <= 120:
        return None
    return json.loads(executor.capabilities or '{}')


def _repository_states(names, mode='commit'):
    executors = frappe.get_all(EXECUTOR, filters={'enabled': 1},
        fields=['capabilities', 'capabilities_at'])
    current = [value for e in executors if (value := _fresh_capabilities(e)) is not None]
    result = {}
    for name in names:
        statuses = [e.get('repositories', {}).get(name) for e in current if mode in e.get('modes', [])]
        previously_configured = any(name in json.loads(e.capabilities or '{}').get('repositories', {}) for e in executors)
        status = ('ready' if 'ready' in statuses else 'unavailable' if 'unavailable' in statuses
                  else 'offline' if previously_configured or not current else 'not_configured')
        message = {'ready': '本机仓库已就绪', 'unavailable': '已配置路径不可用，请检查目录或 Git 仓库',
            'not_configured': '本机尚未配置此仓库路径，或执行端不支持此审查方式',
            'offline': '执行端离线或尚未上报仓库检查，请启动或升级后重启执行端'}[status]
        result[name] = {'status': status, 'message': message,
            'auto_sync': any(name in e.get('managed_repositories', []) for e in current if e.get('repositories', {}).get(name) == 'ready')}
    return result


def _require_repositories(names, mode='commit'):
    unavailable = [(name, state) for name, state in _repository_states(set(names), mode).items()
                   if state['status'] != 'ready']
    if unavailable:
        description = '；'.join(name + '：' + state['message'] for name, state in unavailable)
        frappe.throw('仓库检查未通过：' + description + '。请打开「仓库设置」完成配置并重新检查；未创建或重试任务。')


@frappe.whitelist(methods=['GET'])
def repository_readiness():
    require_manager()
    repos = frappe.get_all('Codeup Repository', filters={'is_active': 1},
        fields=['name', 'repository_name', 'default_branch'], order_by='repository_name')
    states, scans = _repository_states([r.name for r in repos]), _repository_states([r.name for r in repos], 'scan')
    capable = _preparation_executors()
    preparations = frappe.get_all(PREPARATION, fields=['name', 'repository', 'status', 'error', 'lease_until', 'modified'],
        order_by='creation desc', limit_page_length=1000)
    latest = {}
    for item in preparations:
        if item.status == 'preparing' and item.lease_until and get_datetime(item.lease_until) <= now_datetime():
            item.status, item.error = 'failed', '准备任务已超时，请重试'
        latest.setdefault(item.repository, {k: item.get(k) for k in ('name', 'status', 'error', 'modified')})
    for repo in repos:
        repo['readiness'] = states[repo.name]
        repo['scan_readiness'] = scans[repo.name]
        repo['can_prepare'] = bool(capable)
        repo['preparation'] = latest.get(repo.name)
        repo['preparation_executor'] = capable[0].label if capable else ''
    return repos


@frappe.whitelist(allow_guest=True, methods=['POST'])
def report_repositories(repositories, modes=None, supports_preparation=0, managed_repositories=None, environment=None):
    executor = _executor()
    repositories = _parse(repositories)
    modes = _parse(modes) if modes is not None else ['commit', 'scan']
    managed_repositories = _parse(managed_repositories) if managed_repositories is not None else []
    if (not isinstance(repositories, dict) or len(repositories) > 1000 or
            any(not isinstance(k, str) or len(k) > 140 or v not in ('ready', 'unavailable') for k, v in repositories.items()) or
            not isinstance(modes, list) or any(m not in ('commit', 'scan') for m in modes) or
            not isinstance(managed_repositories, list) or len(managed_repositories) > 1000 or
            any(not isinstance(k, str) or k not in repositories for k in managed_repositories)):
        frappe.throw('仓库检查结果无效')
    document = frappe.get_doc(EXECUTOR, executor)
    # 管理端可能刚点过「一键检查/一键配置」，本轮上报顺带取走并清空请求。
    # 用 get() 读新字段：还没执行 bench migrate 的旧库也能继续上报。
    request = document.get('environment_request') or ''
    environment = _parse(environment) if environment is not None else None
    if environment is not None and (not isinstance(environment, dict) or len(_json(environment)) > 200_000):
        frappe.throw('环境检查结果无效')
    values = {'capabilities': _json({'repositories': repositories, 'modes': modes,
        'supports_preparation': bool(frappe.utils.cint(supports_preparation)),
        'managed_repositories': managed_repositories}), 'capabilities_at': now_datetime()}
    if environment is not None:
        values.update({'environment': _json(environment), 'environment_at': now_datetime()})
    if request:
        values['environment_request'] = ''
    frappe.db.set_value(EXECUTOR, executor, values, update_modified=False)
    return {'ok': True, 'request': request,
        'settings': {'data_root': document.get('data_root') or '',
            'revision': frappe.utils.cint(document.get('settings_revision')) or 1}}


def _executor_rows():
    return frappe.get_all(EXECUTOR, filters={'enabled': 1},
        fields=['name', 'label', 'last_seen', 'tool_version', 'capabilities', 'capabilities_at',
            'data_root', 'settings_revision', 'environment', 'environment_at', 'environment_request'],
        order_by='last_seen desc')


def _online_executor():
    """优先选能力上报仍然新鲜的执行端；离线时返回 None。"""
    for row in _executor_rows():
        if _fresh_capabilities(row) is not None:
            return row
    return None


@frappe.whitelist(methods=['GET'])
def environment_status():
    require_manager()
    rows = _executor_rows()
    primary = _online_executor() or (rows[0] if rows else None)
    if not primary:
        return {'executor': None, 'environment': None, 'data_root': {'configured': '', 'reported': ''},
            'repositories': [], 'request': {'mode': '', 'requested_at': None}}
    capabilities = _parse(primary.get('capabilities')) or {}
    if not isinstance(capabilities, dict):
        capabilities = {}
    environment = _parse(primary.get('environment')) if primary.get('environment') else None
    if not isinstance(environment, dict):
        environment = None
    repositories = environment_rows(
        [(repo.name, repo.repository_name) for repo in frappe.get_all('Codeup Repository',
            filters={'is_active': 1}, fields=['name', 'repository_name'], order_by='repository_name')],
        capabilities, environment)
    return {'executor': {'name': primary.name, 'label': primary.label or primary.name,
            'online': _online_executor() is not None, 'tool_version': primary.tool_version or '',
            'last_seen': str(primary.last_seen or '')},
        'environment': environment,
        'data_root': {'configured': primary.data_root or '',
            'reported': (environment or {}).get('data_root', '')},
        'repositories': repositories,
        'request': {'mode': primary.environment_request or '', 'requested_at': None}}


@frappe.whitelist(methods=['POST'])
def request_environment(mode='check'):
    require_manager()
    try:
        mode = normalize_action(mode)
    except ValueError as error:
        frappe.throw(str(error))
    executor = _online_executor()
    if not executor:
        frappe.throw('本机执行端不在线，请先启动执行端再重试')
    frappe.db.set_value(EXECUTOR, executor.name, 'environment_request', mode, update_modified=False)
    return {'ok': True, 'executor': executor.label or executor.name, 'mode': mode}


@frappe.whitelist(methods=['POST'])
def save_environment_settings(data_root=''):
    require_manager()
    try:
        value = normalize_data_root(data_root)
    except ValueError as error:
        frappe.throw(str(error))
    rows = _executor_rows()
    executor = _online_executor() or (rows[0] if rows else None)
    if not executor:
        frappe.throw('还没有注册本机执行端，请先在服务器命令行完成一次本地配置')
    revision = (frappe.utils.cint(executor.get('settings_revision')) or 1) + 1
    frappe.db.set_value(EXECUTOR, executor.name,
        {'data_root': value, 'settings_revision': revision}, update_modified=False)
    return {'ok': True, 'data_root': value, 'revision': revision}


def _preparation_executors():
    rows = frappe.get_all(EXECUTOR, filters={'enabled': 1},
        fields=['name', 'label', 'capabilities', 'capabilities_at'], order_by='last_seen desc')
    return [row for row in rows if (_fresh_capabilities(row) or {}).get('supports_preparation')]


@frappe.whitelist(methods=['POST'])
def prepare_repository(repository, executor=None):
    require_manager()
    repo = frappe.get_doc('Codeup Repository', repository)
    if not repo.is_active:
        frappe.throw('仓库已停用')
    capable = [e for e in _preparation_executors() if not executor or e.name == executor]
    if not capable:
        frappe.throw('没有支持一键准备的在线执行端，请升级并重启本机执行端')
    executor = capable[0].name
    frappe.db.sql('select name from `tabCode Review Executor` where name=%s for update', executor)
    jobs = frappe.get_all(PREPARATION, filters={'repository': repository, 'executor': executor,
        'status': ['in', ['queued', 'preparing']]}, fields=['name', 'status', 'lease_until'])
    for job in jobs:
        if job.status == 'preparing' and job.lease_until and get_datetime(job.lease_until) <= now_datetime():
            frappe.db.set_value(PREPARATION, job.name, {'status': 'failed', 'error': '准备任务已超时，请重试'})
        else:
            return {'name': job.name, 'status': job.status}
    job = _insert(PREPARATION, repository=repository, executor=executor, status='queued', requested_by=frappe.session.user)
    return {'name': job.name, 'status': 'queued'}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def claim_repository_preparation():
    executor = _executor()
    _expire()
    frappe.db.sql('select name from `tabCode Review Executor` where name=%s for update', executor)
    if not (_fresh_capabilities(frappe.get_doc(EXECUTOR, executor)) or {}).get('supports_preparation'):
        return None
    if frappe.db.exists(ATTEMPT, {'executor': executor, 'status': ['in', ACTIVE]}):
        return None
    frappe.db.sql("""update `tabCode Review Repository Preparation` set status='failed', error='准备任务已超时，请重试'
        where executor=%s and status='preparing' and lease_until < %s""", (executor, now_datetime()))
    if frappe.db.exists(PREPARATION, {'executor': executor, 'status': 'preparing'}):
        return None
    rows = frappe.db.sql("""select name from `tabCode Review Repository Preparation`
        where executor=%s and status='queued' order by creation limit 1 for update""", executor)
    if not rows:
        return None
    job = frappe.get_doc(PREPARATION, rows[0][0])
    token = secrets.token_urlsafe(32)
    frappe.db.set_value(PREPARATION, job.name, {'status': 'preparing', 'error': '',
        'lease_hash': _hash(token), 'lease_until': add_to_date(now_datetime(), seconds=90)})
    return {'name': job.name, 'repository': job.repository, 'lease_token': token}


def _preparation_lease(name, lease_token, allow_finished=False):
    executor = _executor()
    frappe.db.sql('select name from `tabCode Review Repository Preparation` where name=%s for update', name)
    job = frappe.get_doc(PREPARATION, name)
    finished = allow_finished and job.status == 'completed'
    if (job.executor != executor or not isinstance(lease_token, str) or
            not hmac.compare_digest(job.lease_hash or '', _hash(lease_token)) or
            (not finished and (job.status != 'preparing' or not job.lease_until or get_datetime(job.lease_until) <= now_datetime()))):
        frappe.throw('仓库准备租约已失效', frappe.PermissionError)
    return job


@frappe.whitelist(allow_guest=True, methods=['POST'])
def preparation_heartbeat(name, lease_token):
    job = _preparation_lease(name, lease_token)
    frappe.db.set_value(PREPARATION, job.name, 'lease_until', add_to_date(now_datetime(), seconds=90))
    return {'ok': True}


def _repository_source(repository):
    from dev_workbench.services.review_repository_source import repository_source as source
    return source(repository)


@frappe.whitelist(allow_guest=True, methods=['POST'])
def repository_source(name, lease_token, preparation=0):
    if frappe.utils.cint(preparation):
        repository = _preparation_lease(name, lease_token).repository
    else:
        task, _ = _lease(name, lease_token)
        repository = task.repository
    return _repository_source(repository)


@frappe.whitelist(allow_guest=True, methods=['POST'])
def finish_repository_preparation(name, lease_token, success=0, error='download'):
    job = _preparation_lease(name, lease_token, allow_finished=True)
    if job.status != 'preparing':
        return {'ok': True}
    errors = {'download': '下载失败，请检查 Codeup 凭证、读取权限、空仓库、网络与磁盘空间后重试',
              'timeout': '仓库准备超时，请检查网络后重试', 'configuration': '本机 Git 或缓存目录不可用，请检查 Git 安装与目录权限'}
    success = frappe.utils.cint(success)
    frappe.db.set_value(PREPARATION, job.name, {'status': 'completed' if success else 'failed',
        'error': '' if success else errors.get(error, errors['download'])})
    return {'ok': True}


def _json(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _parse(value):
    return frappe.parse_json(value) if isinstance(value, str) else value


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _admin():
    return frappe.session.user == 'Administrator' or 'System Manager' in frappe.get_roles()


def _visible(task):
    require_manager()
    if task.owner != frappe.session.user and not _admin():
        frappe.throw('无权访问此私有审查记录', frappe.PermissionError)
    return task


def _task(name, lock=False):
    if lock:
        frappe.db.sql('select name from `tabCode Review Task` where name=%s for update', name)
    return frappe.get_doc(TASK, name)


def _insert(doctype, **values):
    return frappe.get_doc(dict(doctype=doctype, **values)).insert(ignore_permissions=True)


def _effective_status(task):
    if task.status in ACTIVE and task.current_attempt:
        until = frappe.db.get_value(ATTEMPT, task.current_attempt, 'lease_until')
        if until and get_datetime(until) <= now_datetime():
            return 'interrupted'
    return task.status


def _executor():
    token = frappe.get_request_header('X-Review-Token') or ''
    if len(token) < 32 or len(token) > 200:
        frappe.throw('执行器认证失败', frappe.AuthenticationError)
    name = frappe.db.get_value(EXECUTOR, {'token_hash': _hash(token), 'enabled': 1}, 'name')
    if not name:
        frappe.throw('执行器凭证已失效', frappe.AuthenticationError)
    frappe.db.set_value(EXECUTOR, name, 'last_seen', now_datetime(), update_modified=False)
    return name


def _lease(name, lease_token, allow_finished=False):
    executor = _executor()
    task = _task(name, lock=True)
    finished = allow_finished and task.status in ('completed', 'partial')
    if (task.status not in ACTIVE and not finished) or not task.current_attempt:
        frappe.throw('任务已停止', frappe.ValidationError)
    attempt = frappe.get_doc(ATTEMPT, task.current_attempt)
    if (attempt.executor != executor or not isinstance(lease_token, str) or
            not hmac.compare_digest(attempt.lease_hash or '', _hash(lease_token)) or
            (not finished and get_datetime(attempt.lease_until) <= now_datetime())):
        frappe.throw('任务租约已失效', frappe.PermissionError)
    return task, attempt


def _expire():
    # 锁顺序统一为 task -> attempt，避免取消/上传与超时处理死锁。
    rows = frappe.db.sql('''select t.name from `tabCode Review Task` t
        inner join `tabCode Review Attempt` a on a.name=t.current_attempt
        where t.status in ('preparing','running') and a.lease_until < %s''', now_datetime())
    for row in rows:
        task = _task(row[0], lock=True)
        if task.status not in ACTIVE:
            continue
        attempt = frappe.get_doc(ATTEMPT, task.current_attempt)
        if get_datetime(attempt.lease_until) > now_datetime():
            continue
        recover = (task.review_mode == 'scan' and frappe.db.count(ATTEMPT,
            {'task': task.name, 'status': 'interrupted'}) < 3)
        frappe.db.set_value(TASK, task.name, 'status', 'queued' if recover else 'interrupted')
        frappe.db.set_value(ATTEMPT, attempt.name, {'status': 'interrupted',
            'finished_at': now_datetime(), 'error': '执行端离线或租约超时，请手动重试'})


def _commit_time(value):
    if not value:
        return ''
    from dev_workbench.services.commit_processor import parse_author_date_beijing
    return parse_author_date_beijing(value)[1]


@frappe.whitelist(methods=['GET'])
def candidates(member, start_date, end_date=None, scope='all'):
    require_manager()
    if member == 'unclaimed':
        frappe.throw('请先认领 Git 身份，再发起审查')
    logs = frappe.get_all('Daily Activity Log', filters={'member': member,
        'activity_date': ['between', [start_date, end_date or start_date]], 'branch_scope': scope},
        fields=['name', 'raw_json', 'member_name'], limit_page_length=500)
    result, seen = [], set()
    for log in logs:
        for commit in json.loads(log.raw_json or '[]'):
            sha, repo = commit.get('id'), commit.get('repository')
            if (repo, sha) not in seen:
                committed_at = commit.get('authored_date') or commit.get('date') or ''
                result.append(dict(activity_log=log.name, member_name=log.member_name,
                    sha=sha, repository=repo, title=commit.get('title'),
                    date=committed_at, committed_at=committed_at))
                seen.add((repo, sha))
    readiness = _repository_states([item['repository'] for item in result])
    for item in result:
        item['readiness'] = readiness[item['repository']]
    return result


@frappe.whitelist(methods=['POST'])
def create_tasks(selections):
    require_manager()
    selections = _parse(selections)
    if not isinstance(selections, list) or not 1 <= len(selections) <= 20:
        frappe.throw('每批请选择 1 至 20 个提交')
    _require_repositories([selection['repository'] for selection in selections])
    result = []
    for selection in selections:
        sha = validate_sha(selection['sha'])
        log = frappe.get_doc('Daily Activity Log', selection['activity_log'])
        if not log.member or log.is_unclaimed:
            frappe.throw('请先认领 Git 身份')
        matches = [c for c in json.loads(log.raw_json or '[]')
                   if c.get('id') == sha and c.get('repository') == selection['repository']]
        if not matches:
            frappe.throw('提交不属于所选成员日报')
        commit = matches[0]
        repo = frappe.get_doc('Codeup Repository', selection['repository'])
        if not repo.is_active:
            frappe.throw('仓库已停用')
        # 固定 parent，模型不能自行选择审查分支或扩大提交范围。
        from dev_workbench.services.codeup_client import CodeupClient
        from dev_workbench.services.token_service import get_codeup_credentials
        credentials = get_codeup_credentials(repo)
        client = CodeupClient(access_token=credentials['access_token'], base_url=credentials['base_url'])
        detail = client.get_commit(credentials['org_id'], repo.repo_id, sha)
        if detail.get('id') != sha or 'parentIds' not in detail:
            frappe.throw('无法确认提交及父版本，请刷新仓库数据')
        parents = detail['parentIds']
        if len(parents) > 1:
            frappe.throw('第一版暂不支持合并提交')
        base = validate_sha(parents[0]) if parents else ''
        committed_at = _commit_time(commit.get('authored_date') or detail.get('authoredDate') or detail.get('committedDate') or commit.get('date'))
        key = review_key(repo.name, base, sha, config_version=frappe.session.user)
        existing = frappe.db.get_value(TASK, {'review_key': key}, 'name')
        if existing:
            result.append(existing)
            continue
        task = _insert(TASK, member=log.member, member_name=log.member_name, project=log.project,
            repository=repo.name, head_sha=sha, base_sha=base, committed_at=committed_at,
            title=commit.get('title', '')[:1000],
            review_key=key, status='queued', review_status='pending')
        result.append(task.name)
    return result


def _scan_client(repository):
    repo = frappe.get_doc('Codeup Repository', repository)
    if not repo.is_active:
        frappe.throw('仓库已停用')
    from dev_workbench.services.codeup_client import CodeupClient
    from dev_workbench.services.token_service import get_codeup_credentials
    credentials = get_codeup_credentials(repo)
    client = CodeupClient(access_token=credentials['access_token'], base_url=credentials['base_url'])
    return repo, client, credentials['org_id']


@frappe.whitelist(methods=['GET'])
def scan_options(repository=None):
    require_manager()
    if not repository:
        return repository_readiness()
    repo, client, org = _scan_client(repository)
    rows = client.list_branches(org, repo.repo_id, all_pages=True)
    return [r['name'] for r in rows if isinstance(r, dict) and r.get('name')]


@frappe.whitelist(methods=['POST'])
def create_scan_task(repository, branch):
    require_manager()
    _require_repositories([repository], 'scan')
    if not isinstance(branch, str) or not branch.strip() or len(branch) > 255:
        frappe.throw('请选择有效分支')
    repo, client, org = _scan_client(repository)
    commits = client.list_commits(org, repo.repo_id, ref_name=branch, per_page=1)
    if not commits:
        frappe.throw('无法确认分支版本')
    sha = validate_sha(commits[0]['id'])
    committed_at = _commit_time(commits[0].get('authoredDate') or commits[0].get('committedDate'))
    key = review_key(repo.name, '', sha, config_version=frappe.session.user + ':scan-v1')
    existing = frappe.db.get_value(TASK, {'review_key': key}, 'name')
    if existing:
        return existing
    task = _insert(TASK, repository=repo.name, review_mode='scan', branch=branch,
        head_sha=sha, base_sha='', committed_at=committed_at,
        title=('全项目扫描 · ' + branch)[:1000],
        review_key=key, status='queued', review_status='pending')
    return task.name


@frappe.whitelist(methods=['GET'])
def list_tasks():
    require_manager()
    # 只读请求不修改状态；领取、心跳负责过期回收。
    filters = {} if _admin() else {'owner': frappe.session.user}
    tasks = frappe.get_all(TASK, filters=filters, fields=['name', 'member_name', 'repository',
        'head_sha', 'committed_at', 'title', 'status', 'review_status', 'creation', 'current_attempt', 'review_mode', 'branch'],
        order_by='creation desc', limit_page_length=200)
    for task in tasks:
        task.status = _effective_status(task)
        counts = frappe.get_all(FINDING, filters={'attempt': task.current_attempt or '-'},
            fields=['decision'], limit_page_length=200)
        task.pending_count = sum(v.decision == 'pending' for v in counts)
        task.confirmed_count = sum(v.decision == 'confirmed' for v in counts)
    executors = frappe.get_all(EXECUTOR, filters={'enabled': 1}, fields=['label', 'last_seen'])
    return {'tasks': tasks, 'executors': executors}


@frappe.whitelist(methods=['GET'])
def get_task(name, attempt_name=None):
    task = _visible(_task(name))
    result = task.as_dict()
    result['status'] = _effective_status(task)
    result['readiness'] = _repository_states([task.repository], task.review_mode or 'commit')[task.repository]
    result['attempts'] = frappe.get_all(ATTEMPT, filters={'task': name},
        fields=['name', 'status', 'started_at', 'finished_at', 'creation'], order_by='creation desc')
    chosen = attempt_name or task.current_attempt
    if chosen:
        attempt = frappe.get_doc(ATTEMPT, chosen)
        if attempt.task != name:
            frappe.throw('审查版本无效', frappe.PermissionError)
        result['attempt'] = {k: attempt.get(k) for k in ('name', 'status', 'materials', 'report',
            'raw_report', 'error', 'tool_version', 'started_at', 'finished_at')}
        if chosen == task.current_attempt and result['status'] == 'interrupted':
            result['attempt']['status'] = 'interrupted'
            result['attempt']['error'] = '执行端离线或租约超时，请手动重试'
        result['findings'] = frappe.get_all(FINDING, filters={'attempt': chosen}, fields=['*'],
            order_by='creation asc', limit_page_length=200)
    return result


@frappe.whitelist(methods=['POST'])
def update_finding(name, decision, note='', feedback=False):
    require_manager()
    finding = frappe.get_doc(FINDING, name)
    task = _visible(_task(finding.task, lock=True))
    if finding.attempt != task.current_attempt:
        frappe.throw('历史报告只读，请复核当前审查结果')
    if decision not in ('pending', 'confirmed', 'ignored') or len(note) > 10000:
        frappe.throw('复核内容无效')
    frappe.db.set_value(FINDING, name, dict(decision=decision, note=note,
        reviewer=frappe.session.user, reviewed_at=now_datetime(),
        feedback_at=now_datetime() if frappe.utils.cint(feedback) else None))
    frappe.db.set_value(TASK, task.name, 'review_status', 'in_progress')
    return {'ok': True}


@frappe.whitelist(methods=['POST'])
def complete_review(name):
    task = _visible(_task(name, lock=True))
    if task.status not in ('completed', 'partial'):
        frappe.throw('请等待 AI 审查完成')
    if frappe.db.exists(FINDING, {'attempt': task.current_attempt, 'decision': 'pending'}):
        frappe.throw('请先处理全部待确认问题')
    frappe.db.set_value(TASK, name, dict(review_status='completed', reviewer=frappe.session.user,
                                        reviewed_at=now_datetime()))
    return {'ok': True}


@frappe.whitelist(methods=['POST'])
def cancel_task(name):
    task = _visible(_task(name, lock=True))
    if task.status not in ('queued', *ACTIVE):
        frappe.throw('任务已经结束')
    frappe.db.set_value(TASK, name, 'status', 'cancelled')
    if task.current_attempt:
        frappe.db.set_value(ATTEMPT, task.current_attempt, {'status': 'cancelled', 'finished_at': now_datetime()})
    return {'ok': True}


@frappe.whitelist(methods=['POST'])
def retry_task(name, restart=0):
    require_manager()
    _expire()
    task = _visible(_task(name, lock=True))
    if task.status in ('queued', *ACTIVE):
        frappe.throw('任务尚未结束')
    _require_repositories([task.repository], task.review_mode or 'commit')
    frappe.db.set_value(TASK, name, {'status': 'queued', 'review_status': 'pending',
        'current_attempt': None, 'reviewed_at': None, 'reviewer': None,
        'checkpoint_generation': (task.get('checkpoint_generation') or 0) + (1 if frappe.utils.cint(restart) else 0)})
    return {'ok': True}


@frappe.whitelist(methods=['POST'])
def register_executor(label='当前电脑'):
    require_manager()
    if not _admin():
        frappe.throw('仅系统管理员可以配置执行器', frappe.PermissionError)
    token = secrets.token_urlsafe(48)
    executor = _insert(EXECUTOR, label=str(label)[:100], token_hash=_hash(token), enabled=1)
    return {'name': executor.name, 'token': token}


@frappe.whitelist(methods=['POST'])
def revoke_executor(name):
    require_manager()
    if not _admin():
        frappe.throw('仅系统管理员可以撤销执行器', frappe.PermissionError)
    frappe.db.set_value(EXECUTOR, name, 'enabled', 0)
    return {'ok': True}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def claim_task(tool_version=''):
    executor = _executor()
    _expire()
    # 每个执行器仅一个活动任务；数据库锁同时保护多进程重复领取。
    frappe.db.sql('select name from `tabCode Review Executor` where name=%s for update', executor)
    if frappe.db.exists(ATTEMPT, {'executor': executor, 'status': ['in', ACTIVE]}):
        return None
    if frappe.db.exists(PREPARATION, {'executor': executor, 'status': 'preparing', 'lease_until': ['>', now_datetime()]}):
        return None
    capability = _fresh_capabilities(frappe.get_doc(EXECUTOR, executor)) or {}
    repositories = tuple(k for k, v in capability.get('repositories', {}).items() if v == 'ready')
    modes = tuple(capability.get('modes', []))
    if not repositories or not modes:
        return None
    rows = frappe.db.sql("""select name from `tabCode Review Task` where status='queued'
        and repository in %s and coalesce(nullif(review_mode,''),'commit') in %s
        order by creation limit 1 for update""", (repositories, modes))
    if not rows:
        return None
    task = _task(rows[0][0])
    token = secrets.token_urlsafe(32)
    attempt = _insert(ATTEMPT, task=task.name, status='preparing', executor=executor,
        lease_hash=_hash(token), lease_until=add_to_date(now_datetime(), seconds=90),
        started_at=now_datetime(), tool_version=str(tool_version)[:100])
    frappe.db.set_value(TASK, task.name, {'status': 'preparing', 'current_attempt': attempt.name})
    return {'name': task.name, 'attempt': attempt.name, 'repository': task.repository,
            'head_sha': task.head_sha, 'base_sha': task.base_sha, 'lease_token': token,
            'review_mode': task.review_mode or 'commit',
            'checkpoint_generation': task.get('checkpoint_generation') or 0}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def heartbeat(name, lease_token):
    task, attempt = _lease(name, lease_token)
    frappe.db.set_value(ATTEMPT, attempt.name, 'lease_until', add_to_date(now_datetime(), seconds=90))
    return {'status': task.status}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def upload_materials(name, lease_token, materials):
    task, attempt = _lease(name, lease_token)
    if task.status != 'preparing':
        frappe.throw('材料已固定，不能再次替换')
    materials = _parse(materials)
    encoded = _json(materials)
    if len(encoded.encode()) > (100_000_000 if task.review_mode == 'scan' else 8_000_000) or materials.get('head_sha') != task.head_sha or materials.get('base_sha') != (task.base_sha or ''):
        frappe.throw('代码材料版本或大小无效')
    if not isinstance(materials.get('manifest'), dict) or len(materials['manifest']) > (10000 if task.review_mode == 'scan' else 500):
        frappe.throw('材料清单无效')
    for path, info in materials['manifest'].items():
        safe_path(path)
        for side in ('old', 'new'):
            value = info.get(side, 0)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 100000:
                frappe.throw('代码行数无效')
    for item in materials.get('files', []):
        safe_path(item['path'])
        if not isinstance(item.get('content'), str):
            frappe.throw('代码材料必须是文本')
    frappe.db.set_value(ATTEMPT, attempt.name, {'materials': encoded, 'status': 'running'})
    frappe.db.set_value(TASK, name, 'status', 'running')
    return {'ok': True}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def upload_report(name, lease_token, report, raw_report=''):
    task, attempt = _lease(name, lease_token, allow_finished=True)
    if task.status in ('completed', 'partial'):
        normalized = validate_report(_parse(report), json.loads(attempt.materials)['manifest'])
        if json.loads(attempt.report) != normalized:
            frappe.throw('报告已经固定，不能覆盖')
        return {'ok': True}
    if task.status != 'running' or not attempt.materials:
        frappe.throw('请先上传材料')
    if len(raw_report.encode('utf-8')) > (20_000_000 if task.review_mode == 'scan' else 1_000_000):
        frappe.throw('原始报告过大')
    normalized = validate_report(_parse(report), json.loads(attempt.materials)['manifest'])
    for item in normalized['findings']:
        _insert(FINDING, task=name, attempt=attempt.name, **item, decision='pending')
    status = 'partial' if normalized['partial'] else 'completed'
    frappe.db.set_value(ATTEMPT, attempt.name, dict(report=_json(normalized), raw_report=raw_report,
        status=status, finished_at=now_datetime()))
    frappe.db.set_value(TASK, name, 'status', status)
    return {'ok': True}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def fail_attempt(name, lease_token, error='执行失败', raw_report=''):
    task, attempt = _lease(name, lease_token)
    # 执行器只传固定错误代码；不保存可能含认证信息的 stderr。
    allowed = {'missing_repository': '本机尚未配置此仓库路径', 'authentication': 'Claude Code 认证失败',
        'timeout': '审查超时', 'invalid_report': '审查报告解析失败', 'execution': '执行失败，请查看本机诊断',
        'model_configuration': '本机模型配置无效，请在执行环境中检查 JSON 格式、模型名及第三方接口配置；修正后重新审查',
        'repository_sync': '自动同步仓库版本失败，请在仓库设置中重新准备，并检查 Codeup 凭证、权限及网络'}
    frappe.db.set_value(ATTEMPT, attempt.name, dict(status='failed', error=allowed.get(error, allowed['execution']),
        raw_report=str(raw_report)[:1_000_000], finished_at=now_datetime()))
    frappe.db.set_value(TASK, name, 'status', 'failed')
    return {'ok': True}
