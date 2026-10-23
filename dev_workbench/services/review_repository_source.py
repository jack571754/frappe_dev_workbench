"""Git 下载源校验；凭证只返回给持有有效任务租约的本机执行端。"""
from urllib.parse import urlparse


def validate_source_url(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 33 for c in url):
        raise ValueError('仓库下载地址无效')
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'codeup.aliyun.com' or
            parsed.port not in (None, 443) or parsed.username or parsed.password or
            parsed.query or parsed.fragment or not parsed.path.strip('/')):
        raise ValueError('仅支持不含凭证的 Codeup HTTPS 地址')
    return url


def repository_source(repository):
    from dev_workbench.api.v1.code_review import _scan_client
    from dev_workbench.services.token_service import get_codeup_credentials
    repo, client, org = _scan_client(repository)
    url = validate_source_url(client.get_repository(org, repo.repo_id).get('httpUrlToRepo'))
    return {'url': url, 'access_token': get_codeup_credentials(repo)['access_token']}
