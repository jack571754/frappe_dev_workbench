# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import os
import random
import time

import frappe
import requests
from frappe import _


class CodeupAPIError(Exception):
	"""Codeup OpenAPI 调用异常"""

	def __init__(self, message, status_code=None, error_code=None, raw_response=None, code=None):
		super().__init__(message)
		self.message = message
		self.status_code = status_code or code
		self.error_code = error_code or code
		self.raw_response = raw_response

	def __str__(self):
		if self.status_code:
			return f"[{self.status_code}] {self.message}"
		return self.message


class CodeupClient:
	"""
	阿里云云效 Codeup OpenAPI 客户端
	支持 OpenAPI 鉴权 (x-yunxiao-token)、分页遍历、429 指数退避重试和友好错误提示
	"""

	DEFAULT_BASE_URL = "https://openapi-rdc.aliyuncs.com"

	def __init__(
		self,
		access_token=None,
		base_url=None,
		max_retries=3,
		backoff_factor=1.5,
		timeout=15,
	):
		"""
		初始化 Codeup 客户端
		:param access_token: 个人访问令牌 (x-yunxiao-token)
		:param base_url: Codeup OpenAPI Base URL
		:param max_retries: 429 限流和瞬时错误最大重试次数
		:param backoff_factor: 指数退避基数
		:param timeout: HTTP 请求超时秒数
		"""
		global_cfg = {}
		try:
			from dev_workbench.services.token_service import get_codeup_settings

			global_cfg = get_codeup_settings()
		except Exception:
			pass

		self.access_token = (
			access_token
			or global_cfg.get("access_token")
			or getattr(frappe.conf, "codeup_access_token", None)
			or os.environ.get("CODEUP_ACCESS_TOKEN")
		)
		self.base_url = (
			base_url
			or global_cfg.get("base_url")
			or getattr(frappe.conf, "codeup_base_url", None)
			or os.environ.get("CODEUP_BASE_URL")
			or self.DEFAULT_BASE_URL
		).rstrip("/")
		self.max_retries = max_retries
		self.backoff_factor = backoff_factor
		self.timeout = timeout
		self.logger = frappe.logger("dev_workbench")

	def _get_headers(self, token_override=None):
		token = token_override or self.access_token
		headers = {
			"Content-Type": "application/json",
			"Accept": "application/json",
		}
		if token:
			headers["x-yunxiao-token"] = token
		return headers

	def _extract_error_message(self, response):
		try:
			data = response.json()
			if isinstance(data, dict):
				return (
					data.get("errorMessage")
					or data.get("error_message")
					or data.get("message")
					or data.get("error")
					or data.get("errorCode")
					or response.text
				)
		except Exception:
			pass
		return response.text or f"HTTP {response.status_code}"

	def _request(self, method, endpoint, params=None, json_data=None, token_override=None):
		"""
		发送 HTTP 请求并处理 429 退避重试与错误格式化
		"""
		if endpoint.startswith("http://") or endpoint.startswith("https://"):
			url = endpoint
		else:
			url = f"{self.base_url}/{endpoint.lstrip('/')}"

		headers = self._get_headers(token_override)

		for attempt in range(self.max_retries + 1):
			try:
				res = requests.request(
					method=method,
					url=url,
					headers=headers,
					params=params,
					json=json_data,
					timeout=self.timeout,
				)

				# 429 限流处理: 指数退避重试
				if res.status_code == 429:
					if attempt < self.max_retries:
						retry_after = res.headers.get("Retry-After")
						if retry_after and retry_after.isdigit():
							wait_secs = float(retry_after)
						else:
							wait_secs = self.backoff_factor * (2**attempt) + random.uniform(0.1, 0.5)

						self.logger.warning(
							f"Codeup API 触发 429 限流: {url}, 即将等待 {wait_secs:.2f}s 进行第 {attempt + 1}/{self.max_retries} 次重试"
						)
						time.sleep(wait_secs)
						continue
					else:
						err_msg = self._extract_error_message(res)
						raise CodeupAPIError(
							f"Codeup API 请求触发限流 (429)，重试 {self.max_retries} 次后仍未恢复: {err_msg}",
							status_code=429,
							raw_response=res.text,
						)

				# 401 鉴权失效
				if res.status_code == 401:
					err_msg = self._extract_error_message(res)
					raise CodeupAPIError(
						f"Codeup 访问令牌无效或已过期 (401 Unauthorized): {err_msg}",
						status_code=401,
						raw_response=res.text,
					)

				# 403 权限不足
				if res.status_code == 403:
					err_msg = self._extract_error_message(res)
					raise CodeupAPIError(
						f"Codeup 访问权限不足 (403 Forbidden): {err_msg}",
						status_code=403,
						raw_response=res.text,
					)

				# 404 资源不存在
				if res.status_code == 404:
					err_msg = self._extract_error_message(res)
					raise CodeupAPIError(
						f"Codeup 请求资源不存在 (404 Not Found): {url} - {err_msg}",
						status_code=404,
						raw_response=res.text,
					)

				# 其他 4xx / 5xx
				if res.status_code >= 400:
					err_msg = self._extract_error_message(res)
					raise CodeupAPIError(
						f"Codeup API 请求失败 (HTTP {res.status_code}): {err_msg}",
						status_code=res.status_code,
						raw_response=res.text,
					)

				# 成功返回 JSON
				try:
					data = res.json()
				except Exception:
					return res.text

				return data

			except requests.RequestException as e:
				if attempt < self.max_retries:
					wait_secs = self.backoff_factor * (2**attempt)
					self.logger.warning(
						f"Codeup 网络连接异常 ({e})，等待 {wait_secs:.2f}s 进行第 {attempt + 1}/{self.max_retries} 次重试"
					)
					time.sleep(wait_secs)
					continue
				raise CodeupAPIError(f"Codeup OpenAPI 网络请求异常，无法连接服务器: {e!s}")

	def _unwrap_result(self, response_data):
		"""解包 Codeup OpenAPI 返回体，提取 result 字段"""
		if isinstance(response_data, dict):
			if "result" in response_data:
				return response_data["result"]
		return response_data

	def list_repositories(self, org_id, page=1, per_page=50, search=None, all_pages=False):
		"""
		获取指定组织的代码库列表
		:param org_id: Codeup 组织 ID
		:param page: 页码
		:param per_page: 每页数量
		:param search: 搜索关键词
		:param all_pages: 是否自动遍历所有分页
		"""
		if not org_id:
			raise CodeupAPIError("缺少必需参数: org_id")

		endpoint = f"/oapi/v1/codeup/organizations/{org_id}/repositories"

		if not all_pages:
			params = {"page": page, "perPage": per_page}
			if search:
				params["search"] = search
			resp = self._request("GET", endpoint, params=params)
			return self._unwrap_result(resp) or []

		# 遍历所有分页
		all_repos = []
		current_page = 1
		max_limit = 1000

		while len(all_repos) < max_limit:
			params = {"page": current_page, "perPage": per_page}
			if search:
				params["search"] = search
			resp = self._request("GET", endpoint, params=params)
			items = self._unwrap_result(resp) or []
			if not items:
				break
			all_repos.extend(items)
			if len(items) < per_page:
				break
			current_page += 1

		return all_repos

	def list_branches(
		self,
		org_id,
		repo_id,
		page=1,
		per_page=100,
		search=None,
		sort="name_asc",
		all_pages=False,
	):
		"""
		获取指定代码库的分支列表
		:param org_id: Codeup 组织 ID
		:param repo_id: 代码库 ID 或 URL 编码全路径
		:param page: 页码
		:param per_page: 每页数量
		:param search: 搜索关键词
		:param sort: 排序方式 (name_asc, updated_asc, updated_desc)
		:param all_pages: 是否自动遍历所有分页
		"""
		if not org_id or not repo_id:
			raise CodeupAPIError("缺少必需参数: org_id 或 repo_id")

		endpoint = f"/oapi/v1/codeup/organizations/{org_id}/repositories/{repo_id}/branches"

		if not all_pages:
			params = {"page": page, "perPage": per_page, "sort": sort}
			if search:
				params["search"] = search
			resp = self._request("GET", endpoint, params=params)
			return self._unwrap_result(resp) or []

		all_branches = []
		current_page = 1
		max_limit = 2000

		while len(all_branches) < max_limit:
			params = {"page": current_page, "perPage": per_page, "sort": sort}
			if search:
				params["search"] = search
			resp = self._request("GET", endpoint, params=params)
			items = self._unwrap_result(resp) or []
			if not items:
				break
			all_branches.extend(items)
			if len(items) < per_page:
				break
			current_page += 1

		return all_branches

	def list_commits(
		self,
		org_id,
		repo_id,
		ref_name="master",
		since=None,
		until=None,
		page=1,
		per_page=50,
		all_pages=False,
	):
		"""
		按分支、时间范围、分页获取提交历史列表
		:param org_id: Codeup 组织 ID
		:param repo_id: 代码库 ID 或 URL 编码全路径
		:param ref_name: 分支名、Tag 或 Commit SHA
		:param since: 开始时间 (ISO 8601 或 YYYY-MM-DDTHH:MM:SSZ)
		:param until: 结束时间 (ISO 8601 或 YYYY-MM-DDTHH:MM:SSZ)
		:param page: 页码
		:param per_page: 每页条数
		:param all_pages: 是否自动遍历所有分页
		"""
		if not org_id or not repo_id:
			raise CodeupAPIError("缺少必需参数: org_id 或 repo_id")

		endpoint = f"/oapi/v1/codeup/organizations/{org_id}/repositories/{repo_id}/commits"

		if not all_pages:
			params = {"refName": ref_name or "master", "page": page, "perPage": per_page}
			if since:
				params["since"] = since
			if until:
				params["until"] = until
			resp = self._request("GET", endpoint, params=params)
			return self._unwrap_result(resp) or []

		all_commits = []
		current_page = 1
		max_limit = 5000

		while len(all_commits) < max_limit:
			params = {
				"refName": ref_name or "master",
				"page": current_page,
				"perPage": per_page,
			}
			if since:
				params["since"] = since
			if until:
				params["until"] = until

			resp = self._request("GET", endpoint, params=params)
			items = self._unwrap_result(resp) or []
			if not items:
				break
			all_commits.extend(items)
			if len(items) < per_page:
				break
			current_page += 1

		return all_commits

	def get_commit(self, org_id, repo_id, sha):
		"""
		获取单个提交详情（含 stats: additions, deletions, total 等）
		:param org_id: Codeup 组织 ID
		:param repo_id: 代码库 ID
		:param sha: Commit SHA
		"""
		if not org_id or not repo_id or not sha:
			raise CodeupAPIError("缺少必需参数: org_id, repo_id 或 sha")

		endpoint = f"/oapi/v1/codeup/organizations/{org_id}/repositories/{repo_id}/commits/{sha}"
		resp = self._request("GET", endpoint)
		return self._unwrap_result(resp)

	def list_members(self, org_id, page=1, per_page=50, all_pages=False):
		"""
		获取企业/组织成员列表 (邮箱、姓名、状态)
		:param org_id: Codeup 组织 ID
		:param page: 页码
		:param per_page: 每页条数
		:param all_pages: 是否自动遍历所有分页
		"""
		if not org_id:
			raise CodeupAPIError("缺少必需参数: org_id")

		endpoint = f"/oapi/v1/codeup/organizations/{org_id}/members"

		if not all_pages:
			params = {"page": page, "perPage": per_page}
			resp = self._request("GET", endpoint, params=params)
			return self._unwrap_result(resp) or []

		all_members = []
		current_page = 1
		max_limit = 2000

		while len(all_members) < max_limit:
			params = {"page": current_page, "perPage": per_page}
			resp = self._request("GET", endpoint, params=params)
			items = self._unwrap_result(resp) or []
			if not items:
				break
			all_members.extend(items)
			if len(items) < per_page:
				break
			current_page += 1

		return all_members

	def list_repository_members(self, org_id, repo_id, page=1, per_page=50, all_pages=False):
		"""
		获取指定代码库成员列表
		"""
		if not org_id or not repo_id:
			raise CodeupAPIError("缺少必需参数: org_id 或 repo_id")

		endpoint = f"/oapi/v1/codeup/organizations/{org_id}/repositories/{repo_id}/members"
		if not all_pages:
			params = {"page": page, "perPage": per_page}
			resp = self._request("GET", endpoint, params=params)
			return self._unwrap_result(resp) or []

		all_members = []
		current_page = 1
		while len(all_members) < 2000:
			params = {"page": current_page, "perPage": per_page}
			resp = self._request("GET", endpoint, params=params)
			items = self._unwrap_result(resp) or []
			if not items:
				break
			all_members.extend(items)
			if len(items) < per_page:
				break
			current_page += 1
		return all_members

	def list_organizations(self):
		"""
		获取当前用户所在的企业 / 组织列表
		"""
		endpoint = "/oapi/v1/platform/organizations"
		resp = self._request("GET", endpoint)
		return self._unwrap_result(resp) or []

	def get_repository(self, org_id, repo_id):
		"""
		获取指定代码库详情 (含 defaultBranch 等)
		"""
		if not org_id or not repo_id:
			raise CodeupAPIError("缺少必需参数: org_id 或 repo_id")

		endpoint = f"/oapi/v1/codeup/organizations/{org_id}/repositories/{repo_id}"
		resp = self._request("GET", endpoint)
		return self._unwrap_result(resp) or {}

	def list_projex_projects(self, org_id, conditions=None):
		"""
		获取组织内的 Projex 协作项目列表
		"""
		if not org_id:
			raise CodeupAPIError("缺少必需参数: org_id")

		endpoint = f"/oapi/v1/projex/organizations/{org_id}/projects:search"
		resp = self._request("POST", endpoint, json_data=conditions or {})
		return self._unwrap_result(resp) or []

	def verify_token(self, org_id=None):
		"""
		校验当前令牌是否有效
		"""
		if not self.access_token:
			return {"valid": False, "error": "未配置访问令牌"}

		try:
			if org_id:
				self.list_repositories(org_id, page=1, per_page=1)
			else:
				self.list_organizations()
			return {"valid": True, "error": None}
		except CodeupAPIError as e:
			return {"valid": False, "error": str(e), "status_code": e.status_code}
		except Exception as e:
			return {"valid": False, "error": str(e)}
