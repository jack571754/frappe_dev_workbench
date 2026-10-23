# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json
import os
import time

import frappe
import requests
from frappe import _


class FeishuAPIError(Exception):
	"""飞书开放平台 API 调用异常"""

	def __init__(self, message, code=None, raw_response=None):
		super().__init__(message)
		self.message = message
		self.code = code
		self.raw_response = raw_response

	def __str__(self):
		if self.code:
			return f"[{self.code}] {self.message}"
		return self.message


def get_feishu_credentials():
	"""
	获取飞书应用凭据 (app_id, app_secret)
	按优先级查找：
	1. Dev Workbench Settings DocType
	2. Social Login Key (provider="feishu")
	3. 环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET
	"""
	app_id = ""
	app_secret = ""

	# 1. 尝试从 Dev Workbench Settings 获取
	try:
		if frappe.db and frappe.db.exists("DocType", "Dev Workbench Settings"):
			doc = frappe.get_single("Dev Workbench Settings")
			app_id = doc.get("feishu_app_id") or ""
			app_secret = (
				doc.get_password("feishu_app_secret")
				if hasattr(doc, "get_password")
				else doc.get("feishu_app_secret")
			) or ""
	except Exception:
		pass

	# 2. 尝试从 Social Login Key 获取 (PSP 默认配置源)
	if not app_id or not app_secret:
		try:
			if frappe.db and frappe.db.exists("Social Login Key", "feishu"):
				from frappe.utils.password import get_decrypted_password

				login_key = frappe.get_doc("Social Login Key", "feishu")
				if not app_id and login_key.client_id:
					app_id = login_key.client_id
				if not app_secret:
					app_secret = get_decrypted_password("Social Login Key", "feishu", "client_secret")
		except Exception:
			pass

	# 3. 环境变量兜底
	if not app_id:
		app_id = os.environ.get("FEISHU_APP_ID", "")
	if not app_secret:
		app_secret = os.environ.get("FEISHU_APP_SECRET", "")

	return app_id.strip(), app_secret.strip()


class FeishuClient:
	"""
	飞书应用机器人 OpenAPI 客户端
	支持 tenant_access_token 自动获取与缓存、发送富文本/交互卡片消息、以及 429 退避重试
	"""

	FEISHU_HOST = "https://open.feishu.cn"
	TOKEN_URI = "/open-apis/auth/v3/tenant_access_token/internal"
	SEND_MSG_URI = "/open-apis/im/v1/messages"

	def __init__(
		self,
		app_id=None,
		app_secret=None,
		base_url=None,
		session=None,
		max_retries=3,
		backoff_factor=1.5,
		timeout=15,
	):
		creds_app_id, creds_app_secret = get_feishu_credentials()
		self.app_id = app_id or creds_app_id
		self.app_secret = app_secret or creds_app_secret
		self.base_url = (base_url or self.FEISHU_HOST).rstrip("/")
		self.session = session or requests.Session()
		self.max_retries = max_retries
		self.backoff_factor = backoff_factor
		self.timeout = timeout

		self._token = None
		self._token_expires_at = 0

	def get_tenant_access_token(self, force_refresh=False) -> str:
		"""
		获取 tenant_access_token (优先使用内存/缓存，过期自动刷新)
		"""
		now = time.time()
		if not force_refresh and self._token and now < self._token_expires_at:
			return self._token

		if not self.app_id or not self.app_secret:
			raise FeishuAPIError("未配置飞书 App ID 或 App Secret，无法获取 tenant_access_token")

		url = f"{self.base_url}{self.TOKEN_URI}"
		payload = {
			"app_id": self.app_id,
			"app_secret": self.app_secret,
		}

		try:
			resp = self.session.post(url, json=payload, timeout=self.timeout)
		except Exception as e:
			raise FeishuAPIError(f"请求飞书 token 接口失败: {e}")

		if resp.status_code != 200:
			raise FeishuAPIError(
				f"获取飞书 token HTTP 异常: {resp.status_code}",
				code=resp.status_code,
				raw_response=resp.text,
			)

		try:
			data = resp.json()
		except Exception as e:
			raise FeishuAPIError(f"解析飞书 token 响应失败: {e}", raw_response=resp.text)

		code = data.get("code", -1)
		if code != 0:
			msg = data.get("msg", "未知错误")
			raise FeishuAPIError(f"获取飞书 token 业务失败: {msg}", code=code, raw_response=resp.text)

		token = data.get("tenant_access_token")
		expire = data.get("expire", 7200)
		if not token:
			raise FeishuAPIError("飞书 token 响应中未包含 tenant_access_token", raw_response=resp.text)

		self._token = token
		# 提前 5 分钟过期以保证安全
		self._token_expires_at = now + max(expire - 300, 60)
		return self._token

	def send_interactive_card(
		self,
		receive_id: str,
		card_content: dict,
		receive_id_type: str = "open_id",
	) -> dict:
		"""
		通过飞书应用机器人向用户或群聊发送交互卡片消息
		:param receive_id: 接收方 ID (例如 ou_xxxx)
		:param card_content: 飞书交互卡片 JSON 结构体
		:param receive_id_type: ID 类型 ('open_id', 'user_id', 'chat_id')
		:return: response data dict with message_id
		"""
		if not receive_id:
			raise FeishuAPIError("缺少接收方 receive_id")

		token = self.get_tenant_access_token()
		url = f"{self.base_url}{self.SEND_MSG_URI}?receive_id_type={receive_id_type}"
		headers = {
			"Authorization": f"Bearer {token}",
			"Content-Type": "application/json; charset=utf-8",
		}

		card_json_str = json.dumps(card_content, ensure_ascii=False)
		payload = {
			"receive_id": receive_id,
			"msg_type": "interactive",
			"content": card_json_str,
		}

		last_err = None
		for attempt in range(self.max_retries):
			try:
				resp = self.session.post(
					url,
					json=payload,
					headers=headers,
					timeout=self.timeout,
				)

				# 429 限流重试
				if resp.status_code == 429:
					sleep_time = (self.backoff_factor**attempt) + 0.5
					time.sleep(sleep_time)
					continue

				if resp.status_code != 200:
					raise FeishuAPIError(
						f"发送飞书卡片 HTTP 异常: {resp.status_code}",
						code=resp.status_code,
						raw_response=resp.text,
					)

				data = resp.json()
				code = data.get("code", -1)
				if code == 99991663 or code == 99991664:
					# token 过期重新获取一次
					token = self.get_tenant_access_token(force_refresh=True)
					headers["Authorization"] = f"Bearer {token}"
					continue

				if code != 0:
					msg = data.get("msg", "发送失败")
					raise FeishuAPIError(
						f"发送飞书卡片失败: {msg}",
						code=code,
						raw_response=resp.text,
					)

				return data.get("data", {})

			except FeishuAPIError as e:
				last_err = e
				if attempt < self.max_retries - 1 and (e.code == 429 or "timeout" in str(e).lower()):
					time.sleep((self.backoff_factor**attempt) + 0.5)
					continue
				raise
			except Exception as e:
				last_err = FeishuAPIError(f"请求飞书发送消息网络异常: {e}")
				if attempt < self.max_retries - 1:
					time.sleep((self.backoff_factor**attempt) + 0.5)
					continue
				raise last_err

		raise last_err or FeishuAPIError("发送飞书消息失败，已达最大重试次数")

	def send_text_message(
		self,
		receive_id: str,
		text: str,
		receive_id_type: str = "open_id",
	) -> dict:
		"""
		向飞书用户或群组发送纯文本消息
		:param receive_id: 接收者 ID (open_id 或 chat_id)
		:param text: 文本消息正文
		:param receive_id_type: ID 类型
		:return: API 响应数据
		"""
		url = f"{self.base_url}/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
		payload = {
			"receive_id": receive_id,
			"msg_type": "text",
			"content": json.dumps({"text": text}, ensure_ascii=False),
		}

		last_err = None
		for attempt in range(self.max_retries):
			try:
				token = self.get_tenant_access_token()
				headers = {
					"Authorization": f"Bearer {token}",
					"Content-Type": "application/json; charset=utf-8",
				}

				resp = self.session.post(
					url,
					json=payload,
					headers=headers,
					timeout=self.timeout,
				)

				if resp.status_code == 429:
					sleep_time = (self.backoff_factor**attempt) + 0.5
					time.sleep(sleep_time)
					continue

				if resp.status_code != 200:
					raise FeishuAPIError(
						f"发送飞书文本消息 HTTP 异常: {resp.status_code}",
						code=resp.status_code,
						raw_response=resp.text,
					)

				data = resp.json()
				code = data.get("code", -1)
				if code == 99991663 or code == 99991664:
					token = self.get_tenant_access_token(force_refresh=True)
					headers["Authorization"] = f"Bearer {token}"
					continue

				if code != 0:
					msg = data.get("msg", "发送失败")
					raise FeishuAPIError(
						f"发送飞书文本消息失败: {msg}",
						code=code,
						raw_response=resp.text,
					)

				return data.get("data", {})

			except FeishuAPIError as e:
				last_err = e
				if attempt < self.max_retries - 1 and (e.code == 429 or "timeout" in str(e).lower()):
					time.sleep((self.backoff_factor**attempt) + 0.5)
					continue
				raise
			except Exception as e:
				last_err = FeishuAPIError(f"请求飞书发送文本消息网络异常: {e}")
				if attempt < self.max_retries - 1:
					time.sleep((self.backoff_factor**attempt) + 0.5)
					continue
				raise last_err

		raise last_err or FeishuAPIError("发送飞书文本消息失败，已达最大重试次数")


def send_feishu_message_to_managers(title: str, text_content: str):
	"""
	向所有管理者推送飞书文本消息预警
	"""
	managers = frappe.get_all(
		"Project Member",
		filters={"is_active": 1, "is_manager": 1},
		fields=["name", "member_name", "open_id"],
	)

	if not managers:
		frappe.logger("dev_workbench").warning("未找到激活状态的研发工作台管理者，跳过飞书管理者消息发送")
		return

	client = FeishuClient()
	full_msg = f"{title}\n\n{text_content}"
	sent_count = 0

	for m in managers:
		if m.open_id:
			try:
				client.send_text_message(
					receive_id=m.open_id,
					text=full_msg,
					receive_id_type="open_id",
				)
				sent_count += 1
			except Exception as e:
				frappe.logger("dev_workbench").warning(
					f"向管理者 {m.member_name or m.name} 发送飞书通知失败: {e}"
				)

	frappe.logger("dev_workbench").info(f"已完成管理者飞书通知推送，成功发送 {sent_count} 人")
