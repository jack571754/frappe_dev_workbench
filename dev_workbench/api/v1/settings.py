# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from dev_workbench.permissions import require_manager as verify_manager_permission
from dev_workbench.services.ai_client import get_ai_settings, update_ai_settings


@frappe.whitelist(methods=["GET"])
def get_ai_config():
	"""
	获取 AI 模型设置。
	为安全起见，对 API Key 进行脱敏
	"""
	verify_manager_permission()
	settings = get_ai_settings()

	api_key = settings.get("ai_api_key") or ""
	if api_key and len(api_key) > 8:
		masked_key = api_key[:3] + "..." + api_key[-4:]
	elif api_key:
		masked_key = "******"
	else:
		masked_key = ""

	return {
		"ai_enabled": settings.get("ai_enabled", 1),
		"ai_base_url": settings.get("ai_base_url", "https://api.openai.com/v1"),
		"ai_model": settings.get("ai_model", "gpt-4o-mini"),
		"ai_temperature": settings.get("ai_temperature", 0.3),
		"ai_max_tokens": settings.get("ai_max_tokens", 150),
		"ai_api_key_masked": masked_key,
		"has_api_key": bool(api_key),
	}


@frappe.whitelist(methods=["POST"])
def save_ai_config():
	"""
	保存 AI 模型设置。
	"""
	verify_manager_permission()

	data = frappe.local.form_dict
	if isinstance(frappe.request.data, (bytes, str)) and frappe.request.data:
		try:
			parsed = json.loads(frappe.request.data)
			if isinstance(parsed, dict):
				data.update(parsed)
		except Exception:
			pass

	update_values = {}
	if "ai_enabled" in data:
		update_values["ai_enabled"] = 1 if int(data.get("ai_enabled", 1)) else 0
	if "ai_base_url" in data:
		update_values["ai_base_url"] = data.get("ai_base_url")
	if "ai_api_key" in data and data.get("ai_api_key") and not data.get("ai_api_key").startswith("***"):
		update_values["ai_api_key"] = data.get("ai_api_key")
	if "ai_model" in data:
		update_values["ai_model"] = data.get("ai_model")
	if "ai_temperature" in data:
		update_values["ai_temperature"] = float(data.get("ai_temperature"))
	if "ai_max_tokens" in data:
		update_values["ai_max_tokens"] = int(data.get("ai_max_tokens"))

	update_ai_settings(update_values)
	return {
		"status": "success",
		"message": _("AI 模型设置保存成功"),
		"settings": get_ai_config(),
	}


@frappe.whitelist(methods=["GET"])
def get_codeup_config():
	"""
	获取 Codeup 全局配置及凭证状态。
	"""
	verify_manager_permission()
	from dev_workbench.services.token_service import get_codeup_settings, get_token_summary

	settings = get_codeup_settings()
	token = settings.get("access_token") or ""

	if token and len(token) > 8:
		masked_token = token[:4] + "..." + token[-4:]
	elif token:
		masked_token = "******"
	else:
		masked_token = ""

	summary = get_token_summary()

	return {
		"codeup_organization_id": settings.get("organization_id") or "64c8b550dcc8d50d3cc7f5b4",
		"codeup_base_url": settings.get("base_url") or "https://codeup.aliyun.com",
		"codeup_token_expires_at": str(settings.get("token_expires_at") or ""),
		"codeup_token_alert_days": settings.get("token_alert_days", 7),
		"codeup_access_token_masked": masked_token,
		"has_access_token": bool(token),
		"summary": summary,
	}


@frappe.whitelist(methods=["GET"])
def get_codeup_repositories():
	"""Return repository configuration without exposing stored access tokens."""
	verify_manager_permission()
	repositories = frappe.get_all(
		"Codeup Repository",
		fields=[
			"name",
			"repository_name",
			"org_id",
			"repo_id",
			"default_branch",
			"is_active",
			"token_expires_at",
		],
		order_by="repository_name asc",
		limit_page_length=100,
	)
	for repository in repositories:
		repository["has_access_token"] = bool(
			frappe.db.get_value("Codeup Repository", repository.name, "access_token")
		)
	return repositories


@frappe.whitelist(methods=["POST"])
def save_codeup_config():
	"""
	保存 Codeup 全局配置。
	"""
	verify_manager_permission()

	data = frappe.local.form_dict
	if isinstance(frappe.request.data, (bytes, str)) and frappe.request.data:
		try:
			parsed = json.loads(frappe.request.data)
			if isinstance(parsed, dict):
				data.update(parsed)
		except Exception:
			pass

	doc = frappe.get_single("Dev Workbench Settings")

	if "codeup_organization_id" in data:
		doc.codeup_organization_id = (data.get("codeup_organization_id") or "").strip()
	if "codeup_base_url" in data:
		doc.codeup_base_url = (data.get("codeup_base_url") or "").strip()
	if "codeup_token_alert_days" in data:
		try:
			doc.codeup_token_alert_days = int(data.get("codeup_token_alert_days", 7))
		except ValueError, TypeError:
			doc.codeup_token_alert_days = 7
	if "codeup_token_expires_at" in data:
		doc.codeup_token_expires_at = data.get("codeup_token_expires_at") or None

	new_token = data.get("codeup_access_token")
	if new_token and not new_token.startswith("***") and "..." not in new_token:
		doc.codeup_access_token = new_token.strip()

	doc.flags.ignore_permissions = True
	doc.save()

	return {
		"status": "success",
		"message": _("Codeup 全局凭证与配置保存成功"),
		"settings": get_codeup_config(),
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_token_status():
	"""
	查询 Codeup 访问令牌全局与各单库状态及预警。
	"""
	verify_manager_permission()
	from dev_workbench.services.token_service import check_token_expiry, get_token_summary

	summary = get_token_summary()
	details = check_token_expiry(send_notification=False)
	return {
		"status": "success",
		"summary": summary,
		"details": details,
	}


@frappe.whitelist(methods=["POST"])
def converge_repo_credentials():
	"""
	收敛现有代码仓库凭证至全局设置：
	清空单库冗余 access_token 与 org_id，全面继承研发工作台全局配置
	"""
	verify_manager_permission()
	from dev_workbench.services.token_service import get_codeup_settings, get_token_summary

	global_cfg = get_codeup_settings()
	global_org = global_cfg.get("organization_id")

	repos = frappe.get_all("Codeup Repository", fields=["name", "access_token", "org_id", "token_expires_at"])
	updated_count = 0
	for r in repos:
		repo_doc = frappe.get_doc("Codeup Repository", r.name)
		changed = False
		if repo_doc.access_token:
			repo_doc.access_token = None
			changed = True
		if repo_doc.org_id == global_org:
			repo_doc.org_id = None
			changed = True
		if repo_doc.token_expires_at and str(repo_doc.token_expires_at) == str(
			global_cfg.get("token_expires_at")
		):
			repo_doc.token_expires_at = None
			changed = True
		if changed:
			repo_doc.flags.ignore_permissions = True
			repo_doc.save()
			updated_count += 1
	return {
		"status": "success",
		"message": _(f"已收敛 {updated_count} 个代码库的认证凭证至全局设置"),
		"updated_count": updated_count,
		"summary": get_token_summary(),
	}
