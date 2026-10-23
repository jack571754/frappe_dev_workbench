# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json
import os
import re

import frappe
import requests
from frappe import _


class AIServiceError(Exception):
	"""AI 服务调用异常"""

	def __init__(self, message, status_code=None, raw_response=None):
		super().__init__(message)
		self.message = message
		self.status_code = status_code
		self.raw_response = raw_response

	def __str__(self):
		if self.status_code:
			return f"[{self.status_code}] {self.message}"
		return self.message


def get_ai_settings():
	"""
	从系统 Dev Workbench Settings DocType 中读取 AI 摘要模型配置
	并提供环境兜底
	"""
	settings = {}
	try:
		if frappe.db and frappe.db.exists("DocType", "Dev Workbench Settings"):
			doc = frappe.get_single("Dev Workbench Settings")
			settings = {
				"ai_enabled": int(doc.get("ai_enabled", 1)),
				"ai_base_url": doc.get("ai_base_url") or "https://api.openai.com/v1",
				"ai_api_key": doc.get_password("ai_api_key")
				if hasattr(doc, "get_password")
				else doc.get("ai_api_key"),
				"ai_model": doc.get("ai_model") or "gpt-4o-mini",
				"ai_temperature": float(doc.get("ai_temperature") or 0.3),
				"ai_max_tokens": int(doc.get("ai_max_tokens") or 150),
			}
	except Exception as e:
		frappe.logger("dev_workbench").warning(f"读取 Dev Workbench Settings 失败，使用默认配置: {e}")

	# 环境变量回退
	if not settings.get("ai_base_url"):
		settings["ai_base_url"] = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
	if not settings.get("ai_api_key"):
		settings["ai_api_key"] = os.environ.get("OPENAI_API_KEY", "")
	if not settings.get("ai_model"):
		settings["ai_model"] = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
	if "ai_enabled" not in settings:
		settings["ai_enabled"] = 1
	if "ai_temperature" not in settings:
		settings["ai_temperature"] = 0.3
	if "ai_max_tokens" not in settings:
		settings["ai_max_tokens"] = 150

	return settings


def update_ai_settings(values):
	"""
	更新 Dev Workbench Settings 中的 AI 配置
	:param values: dict
	"""
	doc = frappe.get_single("Dev Workbench Settings")
	if "ai_enabled" in values:
		doc.ai_enabled = 1 if values["ai_enabled"] else 0
	if "ai_base_url" in values:
		doc.ai_base_url = (values["ai_base_url"] or "").strip().rstrip("/")
	if values.get("ai_api_key"):
		doc.ai_api_key = values["ai_api_key"].strip()
	if "ai_model" in values:
		doc.ai_model = (values["ai_model"] or "").strip()
	if "ai_temperature" in values:
		doc.ai_temperature = float(values["ai_temperature"])
	if "ai_max_tokens" in values:
		doc.ai_max_tokens = int(values["ai_max_tokens"])

	doc.flags.ignore_permissions = True
	doc.save()
	frappe.db.commit()
	return get_ai_settings()


class OpenAIClient:
	"""
	OpenAI 兼容 API 客户端类
	支持任意 OpenAI 兼容的 Base URL (如 OpenAI, 阿里云百炼/通义千问, DeepSeek, Moonshot, Ollama 等)
	"""

	def __init__(
		self,
		base_url=None,
		api_key=None,
		model=None,
		timeout=30,
		session=None,
	):
		settings = get_ai_settings()
		self.base_url = (
			(base_url or settings.get("ai_base_url") or "https://api.openai.com/v1").strip().rstrip("/")
		)
		self.api_key = api_key if api_key is not None else settings.get("ai_api_key", "")
		self.model = model or settings.get("ai_model") or "gpt-4o-mini"
		self.timeout = timeout
		self.temperature = float(settings.get("ai_temperature") or 0.3)
		self.max_tokens = int(settings.get("ai_max_tokens") or 150)
		self.enabled = bool(settings.get("ai_enabled", 1))
		self.session = session or requests.Session()

	def generate_chat_completion(self, messages, temperature=None, max_tokens=None):
		"""
		调用 /chat/completions 接口生成对话补全
		:param messages: list of dicts [{"role": "system", "content": ...}, ...]
		:param temperature: 采样温度 (默认 self.temperature)
		:param max_tokens: 最大生成 Token 数 (默认 self.max_tokens)
		:return: content (str)
		"""
		if not self.enabled:
			raise AIServiceError("AI 摘要生成已禁用 (ai_enabled=0)")

		if not self.api_key:
			raise AIServiceError("未配置 AI 模型 API Key，请在系统设置中配置")

		# 拼接 chat completions 端点
		if self.base_url.endswith("/chat/completions"):
			endpoint = self.base_url
		else:
			endpoint = f"{self.base_url}/chat/completions"

		payload = {
			"model": self.model,
			"messages": messages,
			"temperature": self.temperature if temperature is None else temperature,
			"max_tokens": self.max_tokens if max_tokens is None else max_tokens,
		}

		headers = {
			"Authorization": f"Bearer {self.api_key}",
			"Content-Type": "application/json",
		}

		try:
			response = self.session.post(
				endpoint,
				json=payload,
				headers=headers,
				timeout=self.timeout,
			)
		except requests.exceptions.Timeout as e:
			raise AIServiceError(f"请求 AI 服务接口超时 ({self.timeout}s): {e}")
		except requests.exceptions.ConnectionError as e:
			raise AIServiceError(f"连接 AI 服务端点失败 ({endpoint}): {e}")
		except Exception as e:
			raise AIServiceError(f"调用 AI 服务网络异常: {e}")

		if response.status_code != 200:
			error_text = response.text
			raise AIServiceError(
				f"AI 服务调用失败: HTTP {response.status_code}",
				status_code=response.status_code,
				raw_response=error_text,
			)

		try:
			data = response.json()
			choices = data.get("choices") or []
			if not choices:
				raise AIServiceError("AI 服务未返回有效 choices 内容", raw_response=response.text)
			content = choices[0].get("message", {}).get("content", "")
			return content.strip()
		except Exception as e:
			if isinstance(e, AIServiceError):
				raise
			raise AIServiceError(f"解析 AI 响应 JSON 失败: {e}", raw_response=response.text)


def build_summary_prompt(commits):
	"""
	构造 AI 摘要生成 Prompt
	遵循 ADR 0003：严禁发送代码 diff，仅输入提交信息与文件列表
	:param commits: list of commit dicts or strings
	:return: messages list
	"""
	commit_titles = []
	files_set = set()

	for idx, c in enumerate(commits):
		if isinstance(c, str):
			commit_titles.append(f"{idx + 1}. {c}")
			continue

		# commit dict
		title = c.get("title") or c.get("message") or ""
		if title:
			clean_title = title.split("\n")[0].strip()
			commit_titles.append(f"{len(commit_titles) + 1}. {clean_title}")

		files = c.get("files") or []
		for f in files:
			if isinstance(f, dict):
				p = f.get("path") or f.get("new_path") or f.get("old_path")
			else:
				p = str(f)
			if p:
				files_set.add(p.strip())

	# 若无标题，提供保底提示
	if not commit_titles:
		commit_titles_text = "（无明确提交标题）"
	else:
		commit_titles_text = "\n".join(commit_titles[:30])  # 最多取 30 条避免超出 token

	if not files_set:
		files_text = "（无变更文件路径记录）"
	else:
		# 最多展示 50 个文件路径
		sorted_files = sorted(list(files_set))[:50]
		files_text = "\n".join([f"- {p}" for p in sorted_files])

	system_prompt = (
		"你是一个专业的软件研发效能与工作日报分析助手。\n"
		"根据提供的某位开发者当日的代码提交列表（包含提交说明和涉及的文件路径），生成一句话中文工作摘要。\n"
		"严格要求：\n"
		"1. 只能输出单句话中文摘要，严格控制在 100 个汉字以内，绝对不要换行，不要输出任何如“今日完成了”、“TA完成了”等废话前缀。\n"
		"2. 仅依据给定的提交信息和修改文件列表进行概括，不要臆测未提及的实现细节。\n"
		"3. 严禁发送或推断代码 diff。\n"
		"4. 如果修改涉及多项不同模块工作，使用逗号连接概括核心事项。\n"
		"5. 如果提交较少或仅有格式化/琐碎修改，简述为常规代码维护或优化。"
	)

	user_prompt = (
		f"【提交信息列表】：\n{commit_titles_text}\n\n"
		f"【修改文件列表】：\n{files_text}\n\n"
		"请根据上述提交与文件，输出一句话中文工作摘要（<=100字）："
	)

	return [
		{"role": "system", "content": system_prompt},
		{"role": "user", "content": user_prompt},
	]


def clean_and_truncate_summary(text, max_length=100):
	"""
	清洗并截断摘要，保证为单句话且中文字符数不超过 100 汉字
	"""
	if not text:
		return ""

	# 替换多行或连续空格为单个空格
	cleaned = re.sub(r"\s+", " ", text).strip()

	# 去除首尾的引号、括号、标点
	cleaned = cleaned.strip("\"'“”‘’`#* ")

	# 去除多余前缀
	prefixes = [
		"今日工作摘要：",
		"今日工作摘要:",
		"工作摘要：",
		"工作摘要:",
		"今日主要工作：",
		"今日主要工作:",
		"今天主要工作：",
		"今天主要工作:",
		"今日完成了",
		"今天完成了",
		"该成员今日",
		"该开发者今日",
	]
	for prefix in prefixes:
		if cleaned.startswith(prefix):
			cleaned = cleaned[len(prefix) :].strip()

	# 确保不超过 max_length
	if len(cleaned) > max_length:
		cleaned = cleaned[: max_length - 3] + "..."

	return cleaned
