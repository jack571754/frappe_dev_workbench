# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _

DEFAULT_CODEUP_ORG_ID = "64c8b550dcc8d50d3cc7f5b4"


def get_codeup_settings():
	"""
	获取研发工作台全局 Codeup 认证配置
	:return: dict
	"""
	try:
		settings = frappe.get_single("Dev Workbench Settings")
	except Exception:
		settings = None

	if not settings:
		return {
			"organization_id": DEFAULT_CODEUP_ORG_ID,
			"access_token": None,
			"token_expires_at": None,
			"token_alert_days": 7,
			"base_url": "https://openapi-rdc.aliyuncs.com",
		}

	token = (
		settings.get_password("codeup_access_token")
		if getattr(settings, "codeup_access_token", None)
		else None
	)
	org_id = (getattr(settings, "codeup_organization_id", None) or "").strip() or DEFAULT_CODEUP_ORG_ID
	expires_at = getattr(settings, "codeup_token_expires_at", None)
	alert_days = int(getattr(settings, "codeup_token_alert_days", None) or 7)
	base_url = (getattr(settings, "codeup_base_url", None) or "https://openapi-rdc.aliyuncs.com").strip()

	return {
		"organization_id": org_id,
		"access_token": token,
		"token_expires_at": expires_at,
		"token_alert_days": alert_days,
		"base_url": base_url,
	}


def get_codeup_credentials(repo_doc_or_name=None):
	"""
	统一获取 Codeup 认证凭证与配置信息（实现单库特定覆盖 + 全局回退继承）：
	1. 优先读取单库自身配置 (access_token, org_id, token_expires_at)
	2. 若单库未配置，自动回退继承全局 Dev Workbench Settings (codeup_access_token, codeup_organization_id, codeup_token_expires_at)
	3. 若全局仍未配置，回退环境变量 (CODEUP_ACCESS_TOKEN / CODEUP_ORGANIZATION_ID) 或 site_config

	:param repo_doc_or_name: 可选，Codeup Repository 文档对象或名称
	:return: dict 包含 token, org_id, token_expires_at 以及继承状态标记
	"""
	global_cfg = get_codeup_settings()

	repo_doc = None
	if repo_doc_or_name:
		if isinstance(repo_doc_or_name, str):
			if frappe.db.exists("Codeup Repository", repo_doc_or_name):
				repo_doc = frappe.get_doc("Codeup Repository", repo_doc_or_name)
		elif hasattr(repo_doc_or_name, "doctype") and repo_doc_or_name.doctype == "Codeup Repository":
			repo_doc = repo_doc_or_name
		elif isinstance(repo_doc_or_name, dict):
			repo_doc = frappe._dict(repo_doc_or_name)

	# 1. 尝试提取单库自身配置
	repo_token = None
	repo_org_id = None
	repo_expires_at = None

	if repo_doc:
		get_pw = getattr(repo_doc, "get_password", None)
		if callable(get_pw):
			repo_token = get_pw("access_token") if repo_doc.access_token else None
		else:
			repo_token = repo_doc.get("access_token")
			if (
				repo_token
				and repo_doc.get("name")
				and frappe.db.exists("Codeup Repository", repo_doc.get("name"))
			):
				try:
					full_doc = frappe.get_doc("Codeup Repository", repo_doc.get("name"))
					repo_token = full_doc.get_password("access_token") or repo_token
				except Exception:
					pass

		repo_org_id = (repo_doc.get("org_id") or "").strip() or None
		repo_expires_at = repo_doc.get("token_expires_at") or None

	# 2. 回退继承与判定
	env_token = frappe.conf.get("codeup_access_token") or frappe.conf.get("CODEUP_ACCESS_TOKEN")
	final_token = repo_token or global_cfg["access_token"] or env_token

	final_org_id = repo_org_id or global_cfg["organization_id"] or DEFAULT_CODEUP_ORG_ID
	final_expires_at = repo_expires_at or global_cfg["token_expires_at"]

	return {
		"access_token": final_token,
		"org_id": final_org_id,
		"token_expires_at": final_expires_at,
		"is_token_inherited": bool(not repo_token and global_cfg["access_token"]),
		"is_org_inherited": bool(not repo_org_id or repo_org_id == global_cfg["organization_id"]),
		"is_expiry_inherited": bool(not repo_expires_at and global_cfg["token_expires_at"]),
		"base_url": global_cfg["base_url"],
		"alert_days": global_cfg["token_alert_days"],
	}


def check_token_expiry(repo_name=None, send_notification=True):
	"""
	检查 Codeup 访问令牌有效期（包含全局令牌与单库覆盖令牌）。
	当令牌已过期或距离到期不足预警天数时，触发管理者飞书/系统提醒。

	:param repo_name: 可选，指定检查某个仓库名称
	:param send_notification: 是否发送提醒
	:return: 包含所有仓库及全局令牌检查结果的列表
	"""
	today = frappe.utils.getdate(frappe.utils.nowdate())
	global_cfg = get_codeup_settings()
	alert_days = global_cfg["token_alert_days"]

	results = []
	alerts_to_send = []

	# 1. 如果未指定单一仓库，首先检查全局 Dev Workbench Settings 中的访问令牌
	if not repo_name:
		g_expires = global_cfg["token_expires_at"]
		g_token = global_cfg["access_token"]

		if not g_expires:
			results.append(
				{
					"repository": "__global__",
					"repository_name": "研发工作台全局 Codeup 凭证",
					"token_expires_at": None,
					"days_left": None,
					"status": "not_set" if g_token else "no_token",
					"is_inherited": False,
					"message": "全局未配置访问令牌到期日期" if g_token else "全局尚未配置 Codeup 访问令牌",
				}
			)
		else:
			g_exp_date = frappe.utils.getdate(g_expires)
			days_left = (g_exp_date - today).days

			if days_left < 0:
				g_status = "expired"
				alert_msg = f"【紧急】研发工作台全局 Codeup 访问令牌已于 {g_expires} 过期（已逾期 {abs(days_left)} 天），全部复用该令牌的代码库同步将受阻，请立即更新！"
				alerts_to_send.append(alert_msg)
			elif days_left <= alert_days:
				g_status = "expiring_soon"
				alert_msg = f"【预警】研发工作台全局 Codeup 访问令牌即将在 {days_left} 天后（{g_expires}）到期，请及时续期！"
				alerts_to_send.append(alert_msg)
			else:
				g_status = "valid"
				alert_msg = f"全局 Codeup 访问令牌状态正常（有效剩余 {days_left} 天）"

			results.append(
				{
					"repository": "__global__",
					"repository_name": "研发工作台全局 Codeup 凭证",
					"token_expires_at": str(g_expires),
					"days_left": days_left,
					"status": g_status,
					"is_inherited": False,
					"message": alert_msg,
				}
			)

	# 2. 检查代码仓库
	filters = {"is_active": 1}
	if repo_name:
		filters["name"] = repo_name

	repos = frappe.get_all(
		"Codeup Repository",
		filters=filters,
		fields=["name", "repository_name", "org_id", "repo_id", "token_expires_at", "access_token"],
	)

	has_global_alert = bool(alerts_to_send)

	for repo in repos:
		repo_title = repo.repository_name or repo.name
		creds = get_codeup_credentials(repo)

		expires_at = creds["token_expires_at"]
		is_inherited = creds["is_token_inherited"]

		if not expires_at:
			results.append(
				{
					"repository": repo.name,
					"repository_name": repo_title,
					"token_expires_at": None,
					"days_left": None,
					"status": "not_set",
					"is_inherited": is_inherited,
					"message": f"仓库【{repo_title}】未配置访问令牌到期日期（继承全局配置）"
					if is_inherited
					else f"仓库【{repo_title}】未配置独立访问令牌到期日期",
				}
			)
			continue

		expires_date = frappe.utils.getdate(expires_at)
		days_left = (expires_date - today).days

		if days_left < 0:
			status = "expired"
			alert_msg = f"【紧急】仓库【{repo_title}】Codeup 访问令牌已于 {expires_at} 过期（已逾期 {abs(days_left)} 天），请立即更新！"
			# 如果单库继承全局，且已发出过全局告警，则不重复刷屏
			if not (is_inherited and has_global_alert):
				alerts_to_send.append(alert_msg)
		elif days_left <= alert_days:
			status = "expiring_soon"
			alert_msg = f"【提醒】仓库【{repo_title}】Codeup 访问令牌即将在 {days_left} 天后（{expires_at}）过期，请及时续期！"
			if not (is_inherited and has_global_alert):
				alerts_to_send.append(alert_msg)
		else:
			status = "valid"
			alert_msg = f"仓库【{repo_title}】访问令牌正常（有效剩余 {days_left} 天）"

		results.append(
			{
				"repository": repo.name,
				"repository_name": repo_title,
				"token_expires_at": str(expires_at),
				"days_left": days_left,
				"status": status,
				"is_inherited": is_inherited,
				"message": alert_msg,
			}
		)

	if alerts_to_send and send_notification:
		send_expiry_notifications(alerts_to_send)

	return results


def get_token_summary():
	"""
	获取前端看板呈现专用的 Token 状态摘要
	"""
	today = frappe.utils.getdate(frappe.utils.nowdate())
	global_cfg = get_codeup_settings()
	g_expires = global_cfg["token_expires_at"]
	g_token = global_cfg["access_token"]
	alert_days = global_cfg["token_alert_days"]

	days_left = None
	if g_expires:
		days_left = (frappe.utils.getdate(g_expires) - today).days
		if days_left < 0:
			status = "expired"
		elif days_left <= alert_days:
			status = "expiring_soon"
		else:
			status = "valid"
	else:
		status = "not_set" if g_token else "no_token"

	masked_token = ""
	if g_token:
		if len(g_token) > 8:
			masked_token = g_token[:4] + "..." + g_token[-4:]
		else:
			masked_token = "******"

	# 统计单库覆盖与继承分布
	repos = frappe.get_all(
		"Codeup Repository",
		filters={"is_active": 1},
		fields=["name", "access_token", "org_id", "token_expires_at"],
	)

	override_count = 0
	inherited_count = 0
	for r in repos:
		has_token_override = bool(r.access_token)
		has_org_override = bool(r.org_id and r.org_id != global_cfg["organization_id"])
		if has_token_override or has_org_override:
			override_count += 1
		else:
			inherited_count += 1

	return {
		"global_status": status,
		"global_expires_at": str(g_expires) if g_expires else None,
		"days_left": days_left,
		"alert_days": alert_days,
		"organization_id": global_cfg["organization_id"],
		"has_global_token": bool(g_token),
		"global_token_masked": masked_token,
		"total_repositories": len(repos),
		"inherited_count": inherited_count,
		"override_count": override_count,
		"need_attention": status in ("expired", "expiring_soon"),
	}


def send_expiry_notifications(alerts):
	"""
	向所有研发工作台管理者发送令牌到期提醒
	"""
	logger = frappe.logger("dev_workbench")
	combined_message = "\n".join(alerts)

	logger.warning(f"Codeup 访问令牌到期预警:\n{combined_message}")

	# 1. 查找所有工作台管理者邮箱
	manager_emails = set(
		frappe.db.get_values(
			"Project Member",
			{"is_active": 1, "is_manager": 1},
			"email",
			pluck=True,
		)
	)

	# 查找具有 Dev Workbench Manager 或 System Manager 角色的系统用户
	system_managers = set(
		frappe.db.sql(
			"""
			SELECT distinct parent FROM `tabHas Role`
			WHERE role in ('Dev Workbench Manager', 'System Manager')
			AND parent not in ('Guest', 'Administrator')
			""",
			pluck=True,
		)
	)
	all_recipients = list(manager_emails | system_managers)

	# 2. 为系统用户创建 Notification Log
	for recipient in all_recipients:
		if frappe.db.exists("User", recipient):
			try:
				doc = frappe.new_doc("Notification Log")
				doc.for_user = recipient
				doc.from_user = "Administrator"
				doc.type = "Alert"
				doc.subject = "Codeup 访问令牌即将过期提醒"
				doc.email_content = combined_message
				doc.flags.ignore_permissions = True
				doc.insert()
			except Exception as e:
				logger.error(f"创建 Notification Log 失败 ({recipient}): {e}")

	# 3. 尝试通过飞书应用机器人通知
	try:
		from dev_workbench.services.feishu_client import send_feishu_message_to_managers

		send_feishu_message_to_managers("【研发工作台】Codeup 令牌到期提醒", combined_message)
	except (ImportError, Exception) as e:
		logger.info(f"飞书通知跳过或未就绪: {e}")
