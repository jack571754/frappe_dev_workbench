import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse


class Client:
    def __init__(self, url, token):
        parsed = urlparse(url)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', 'development.localhost')):
            raise ValueError('执行器仅允许 HTTPS 或本机 HTTP 工作台')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('工作台地址不能包含凭证或查询参数')
        self.url, self.token = url.rstrip('/'), token
        # 不走环境代理，避免本机请求和凭证被转发到第三方代理。
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, method, **params):
        data = json.dumps(params, ensure_ascii=False).encode()
        request = urllib.request.Request(self.url + '/api/method/dev_workbench.api.v1.code_review.' + method,
            data=data, headers={'Content-Type': 'application/json', 'X-Review-Token': self.token})
        for attempt in range(3):
            try:
                return self._response(request, method)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                retryable = method in ('heartbeat', 'preparation_heartbeat', 'report_repositories')
                if isinstance(error, urllib.error.HTTPError) and error.code not in (502, 503, 504):
                    retryable = False
                if not retryable or attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))

    def _response(self, request, method):
        with self.opener.open(request, timeout=15) as response:
            payload = json.loads(response.read(10_000_000))
            # Frappe omits message when a whitelisted method returns None.
            if method in ('claim_task', 'claim_repository_preparation') and payload == {}:
                return None
            return payload['message']
