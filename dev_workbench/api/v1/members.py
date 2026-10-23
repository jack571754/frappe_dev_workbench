# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import re

import frappe
import requests
from frappe import _
from frappe.utils import cint, now_datetime

from dev_workbench.permissions import require_manager as _check_manager_permission
from dev_workbench.services.feishu_client import FeishuClient, get_feishu_credentials

FEISHU_HOST = "https://open.feishu.cn"


def _lookup_feishu_contact(email=None, mobile=None):
	"""
	通过精准接口向飞书查询单用户的 open_id / user_id
	使用 POST /open-apis/contact/v3/users/batch_get_id (支持 tenant_access_token)
	"""
	try:
		cli = FeishuClient()
		token = cli.get_tenant_access_token()
		if not token:
			return None

		payload = {}
		if email:
			payload["emails"] = [email.strip()]
		elif mobile:
			payload["mobiles"] = [mobile.strip()]
		else:
			return None

		resp = requests.post(
			f"{cli.base_url}/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id",
			headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
			json=payload,
			timeout=6,
		)
		if resp.status_code == 200:
			data = resp.json()
			if data.get("code") == 0:
				user_list = data.get("data", {}).get("user_list", [])
				if user_list and (
					user_list[0].get("user_id")
					or user_list[0].get("open_id")
					or user_list[0].get("user_id_type")
				):
					u = user_list[0]
					return {
						"user_id": u.get("user_id") or "",
						"open_id": u.get("open_id") or "",
						"mobile": u.get("mobile") or mobile,
						"email": u.get("email") or email,
					}
	except Exception as e:
		frappe.log_error(f"Lookup feishu user exception: {e}", "Dev Workbench")
	return None


@frappe.whitelist(methods=["GET", "POST"])
def search_member_candidates(query=None):
	"""
	【搜索逻辑】搜索候选团队成员：
	支持根据输入的姓名、邮箱、手机号或拼音，在本地用户库和飞书接口中精准检索候选人
	返回结构化候选人列表，标明是否已在团队中、已绑定的 Git 身份及待认领身份
	"""
	_check_manager_permission()

	q = (query or frappe.form_dict.get("query") or "").strip()
	candidates = []
	seen_emails = set()

	# 1. 查询本地 Project Member 建立快速去重与映射表
	existing_members = frappe.get_all(
		"Project Member",
		fields=[
			"name",
			"member_name",
			"email",
			"mobile",
			"user_id",
			"open_id",
			"is_active",
			"is_manager",
			"department",
		],
		limit_page_length=500,
	)
	member_by_email = {m.email.lower(): m for m in existing_members if m.email}
	member_by_name = {m.member_name.lower(): m for m in existing_members if m.member_name}

	# 1.1 若存在搜索关键词，优先归入匹配的已有团队成员
	if q:
		q_lower = q.lower()
		for m in existing_members:
			m_name = (m.member_name or "").lower()
			m_email = (m.email or "").lower()
			m_mobile = m.mobile or ""
			if q_lower in m_name or q_lower in m_email or q_lower in m_mobile:
				if m_email:
					seen_emails.add(m_email)
				candidates.append(
					{
						"member_name": m.member_name,
						"email": m.email,
						"mobile": m.mobile or "",
						"department": m.department or "",
						"user_id": m.user_id or "",
						"open_id": m.open_id or "",
						"is_existing": bool(m.is_active),
						"existing_id": m.name,
						"source": "team",
					}
				)

	# 2. 如果 query 是邮箱或手机号，尝试通过飞书 batch_get_id 精确查询
	feishu_found = None
	if q:
		if "@" in q:
			feishu_found = _lookup_feishu_contact(email=q)
		elif q.replace("+", "").isdigit() and len(q) >= 7:
			feishu_found = _lookup_feishu_contact(mobile=q)

	if feishu_found and feishu_found.get("email"):
		em = feishu_found["email"].lower()
		if em not in seen_emails:
			seen_emails.add(em)
			ex = member_by_email.get(em)
			candidates.append(
				{
					"member_name": (ex.member_name if ex else q.split("@")[0]),
					"email": feishu_found["email"],
					"mobile": feishu_found.get("mobile") or (ex.mobile if ex else ""),
					"department": (ex.department if ex else ""),
					"user_id": feishu_found.get("user_id") or (ex.user_id if ex else ""),
					"open_id": feishu_found.get("open_id") or (ex.open_id if ex else ""),
					"is_existing": bool(ex and ex.is_active),
					"existing_id": ex.name if ex else None,
					"source": "feishu",
				}
			)

	# 3. 在系统 User 表中进行模糊匹配搜索
	params = {}

	if q:
		params["like_q"] = f"%{q}%"
		user_sql = """
			SELECT name, email, full_name, first_name, last_name, mobile_no
			FROM `tabUser`
			WHERE enabled = 1
			  AND (name != 'Administrator')
			  AND (name LIKE %(like_q)s OR email LIKE %(like_q)s OR full_name LIKE %(like_q)s OR mobile_no LIKE %(like_q)s)
			ORDER BY creation DESC
			LIMIT 15
		"""
		system_users = frappe.db.sql(user_sql, params, as_dict=True)
	else:
		# 无 query 时返回最近创建的 10 位系统用户作为初始建议
		system_users = frappe.get_all(
			"User",
			filters={"enabled": 1, "name": ["!=", "Administrator"]},
			fields=["name", "email", "full_name", "first_name", "last_name", "mobile_no"],
			limit=10,
		)

	for su in system_users:
		em = (su.email or su.name or "").strip().lower()
		if not em or em in seen_emails:
			continue
		seen_emails.add(em)

		display_name = (su.full_name or su.first_name or em.split("@")[0]).strip()
		ex = member_by_email.get(em) or member_by_name.get(display_name.lower())

		candidates.append(
			{
				"member_name": display_name,
				"email": su.email or su.name,
				"mobile": su.mobile_no or (ex.mobile if ex else ""),
				"department": su.get("department") or (ex.department if ex else ""),
				"user_id": (ex.user_id if ex else ""),
				"open_id": (ex.open_id if ex else ""),
				"is_existing": bool(ex and ex.is_active),
				"existing_id": ex.name if ex else None,
				"source": "system",
			}
		)

	# 4. 补充待认领 Git 身份与推荐关联合并
	unclaimed = frappe.get_all(
		"Git Identity",
		filters={"status": "待认领"},
		fields=["name", "identity", "identity_type"],
		limit=50,
	)
	unclaimed_by_identity = {u.identity.lower(): u.name for u in unclaimed}

	for c in candidates:
		c_email = (c.get("email") or "").lower()
		matched_unclaimed = []
		if c_email in unclaimed_by_identity:
			matched_unclaimed.append(unclaimed_by_identity[c_email])
		c["unclaimed_git_identities"] = matched_unclaimed

	return candidates


@frappe.whitelist(methods=["POST"])
def add_project_member(
	member_name,
	email,
	mobile=None,
	department=None,
	is_manager=0,
	git_identity=None,
	open_id=None,
	user_id=None,
):
	"""
	【搜索后精准添加】将选定人员添加为研发团队成员
	自动补充飞书 open_id / user_id，并可选直接绑定初始 Git 身份
	"""
	_check_manager_permission()

	member_name = (member_name or "").strip()
	email = (email or "").strip().lower()
	mobile = (mobile or "").strip()

	if not member_name or not email:
		frappe.throw(_("姓名与邮箱为必填项"))

	# 1. 尝试通过飞书补充缺失的 open_id / user_id
	if not open_id or not user_id:
		feishu_info = _lookup_feishu_contact(email=email, mobile=mobile)
		if feishu_info:
			open_id = open_id or feishu_info.get("open_id")
			user_id = user_id or feishu_info.get("user_id")
			mobile = mobile or feishu_info.get("mobile")

	# 2. 检查是否已有记录 (按邮箱或姓名)
	existing_id = frappe.db.get_value("Project Member", {"email": email}, "name")
	if not existing_id:
		existing_id = frappe.db.get_value("Project Member", {"member_name": member_name}, "name")

	if existing_id:
		doc = frappe.get_doc("Project Member", existing_id)
		doc.member_name = member_name
		doc.email = email
		doc.mobile = mobile or doc.mobile
		doc.department = department or doc.department
		doc.is_manager = cint(is_manager)
		doc.is_active = 1  # 确保处于启用状态
		if open_id:
			doc.open_id = open_id
		if user_id:
			doc.user_id = user_id
		doc.save(ignore_permissions=True)
		action = "更新并启用"
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Project Member",
				"member_name": member_name,
				"email": email,
				"mobile": mobile,
				"department": department,
				"is_manager": cint(is_manager),
				"is_active": 1,
				"open_id": open_id,
				"user_id": user_id,
			}
		).insert(ignore_permissions=True)
		action = "添加"

	# 3. 如果提供了 Git 身份，立即为其绑定认领
	git_id_created = None
	if git_identity:
		ident_clean = git_identity.strip()
		if ident_clean:
			id_type = "Email" if "@" in ident_clean else "Username"
			add_git_identity(doc.name, ident_clean, identity_type=id_type)
			git_id_created = ident_clean

	# 4. 自动检查是否有匹配该邮箱的待认领 Git 身份，一并认领
	auto_unclaimed = frappe.get_all(
		"Git Identity",
		filters={"identity": email, "status": "待认领"},
		pluck="name",
	)
	for u_name in auto_unclaimed:
		claim_git_identity(doc.name, u_name)

	return {
		"status": "success",
		"message": f"已成功{action}团队成员: {member_name} ({email})",
		"member": {
			"name": doc.name,
			"member_name": doc.member_name,
			"email": doc.email,
			"mobile": doc.mobile,
			"is_manager": doc.is_manager,
			"git_identity": git_id_created,
		},
	}


@frappe.whitelist(methods=["POST"])
def batch_add_members(raw_text):
	"""
	【批量精准添加】支持输入/粘贴多行文本（邮箱、手机号或姓名 邮箱），定向录入团队
	避免无差别导入全企业无关人员
	"""
	_check_manager_permission()

	raw = (raw_text or frappe.form_dict.get("raw_text") or "").strip()
	if not raw:
		frappe.throw(_("请输入至少一条人员信息（邮箱或姓名）"))

	lines = [line.strip() for line in re.split(r"[\n,;]+", raw) if line.strip()]
	created_count = 0
	updated_count = 0
	errors = []

	for item in lines:
		# 解析每行：支持 "张伟 zhangwei@example.com" 或直接 "zhangwei@example.com"
		parts = item.split()
		if len(parts) >= 2:
			name = parts[0]
			email = parts[1]
			mobile = parts[2] if len(parts) > 2 else None
		else:
			entry = parts[0]
			if "@" in entry:
				name = entry.split("@")[0]
				email = entry
				mobile = None
			else:
				name = entry
				email = f"{entry}@company.local"
				mobile = None

		try:
			res = add_project_member(member_name=name, email=email, mobile=mobile)
			if "添加" in res.get("message", ""):
				created_count += 1
			else:
				updated_count += 1
		except Exception as e:
			errors.append(f"{item}: {e!s}")

	return {
		"status": "success",
		"message": f"批量处理完成：新增 {created_count} 人，更新 {updated_count} 人"
		+ (f"，失败 {len(errors)} 条" if errors else ""),
		"created": created_count,
		"updated": updated_count,
		"errors": errors,
	}


@frappe.whitelist(methods=["POST"])
def remove_project_member(member_id, permanent=0):
	"""
	【安全移除成员】将成员移出团队（置为禁用），避免无关人员继续干扰日报与统计
	"""
	_check_manager_permission()

	if not frappe.db.exists("Project Member", member_id):
		frappe.throw(_("成员不存在"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Project Member", member_id)
	doc.is_active = 0
	doc.save(ignore_permissions=True)

	return {
		"status": "success",
		"message": f"已成功将成员 {doc.member_name} 移出团队",
	}


@frappe.whitelist(methods=["POST"])
def import_feishu_contacts():
	"""
	兼容旧版接口，若全量通讯录权限不足，返回清晰指引并避免卡顿
	"""
	_check_manager_permission()

	app_id, app_secret = get_feishu_credentials()
	feishu_users = []

	if app_id and app_secret:
		try:
			cli = FeishuClient()
			token = cli.get_tenant_access_token()
			if token:
				users_res = requests.get(
					f"{cli.base_url}/open-apis/contact/v3/users?page_size=50",
					headers={"Authorization": f"Bearer {token}"},
					timeout=5,
				)
				if users_res.ok and users_res.json().get("code") == 0:
					feishu_users = users_res.json().get("data", {}).get("items", [])
				elif users_res.status_code == 400 or users_res.json().get("code") == 99991672:
					# 明确检测到全量通讯录只读权限不足
					return {
						"status": "warning",
						"message": "飞书应用尚未开通企业全量通讯录只读权限（需企业管理员在开放平台审批）。现已全面切换为【搜索并添加成员】模式，请使用搜索框精准添加团队研发人员！",
						"suggest_search": True,
					}
		except Exception as e:
			frappe.log_error(f"Feishu contact sync error: {e}", "Dev Workbench")

	# 如果有返回用户才同步，不再全量扫描导入整个 User 表以防混入大量无关人员
	created_count = 0
	updated_count = 0
	for u in feishu_users:
		email = u.get("email") or u.get("enterprise_email")
		if not email:
			continue
		res = add_project_member(
			member_name=u.get("name") or email.split("@")[0],
			email=email,
			mobile=u.get("mobile"),
			user_id=u.get("user_id"),
			open_id=u.get("open_id"),
		)
		if "添加" in res.get("message", ""):
			created_count += 1
		else:
			updated_count += 1

	return {
		"status": "success",
		"message": f"同步完成：新增 {created_count} 位成员，更新 {updated_count} 位成员",
		"created": created_count,
		"updated": updated_count,
	}


@frappe.whitelist(methods=["GET"])
def get_unclaimed_identities():
	"""获取所有待认领的 Git 身份列表"""
	_check_manager_permission()

	identities = frappe.get_all(
		"Git Identity",
		filters={"status": "待认领"},
		fields=["name", "identity", "identity_type", "status", "creation"],
		order_by="creation desc",
	)
	return identities


@frappe.whitelist(methods=["POST"])
def claim_git_identity(member_id, identity_name):
	"""管理者为指定成员认领一个 Git 身份"""
	_check_manager_permission()

	if not frappe.db.exists("Project Member", member_id):
		frappe.throw(_("成员不存在"), frappe.DoesNotExistError)
	if not frappe.db.exists("Git Identity", identity_name):
		frappe.throw(_("Git 身份不存在"), frappe.DoesNotExistError)

	ident_doc = frappe.get_doc("Git Identity", identity_name)
	ident_doc.member = member_id
	ident_doc.status = "已认领"
	ident_doc.claimed_at = now_datetime()
	ident_doc.claimed_by = frappe.session.user
	ident_doc.save(ignore_permissions=True)

	# 1. 回溯更新此前因未归属而记录的 DailyActivityLog
	unclaimed_logs = frappe.get_all(
		"Daily Activity Log",
		filters={"is_unclaimed": 1},
		fields=["name", "raw_json"],
	)
	for ulog in unclaimed_logs:
		if ident_doc.identity in (ulog.raw_json or ""):
			log_doc = frappe.get_doc("Daily Activity Log", ulog.name)
			log_doc.member = member_id
			log_doc.member_name = frappe.db.get_value("Project Member", member_id, "member_name")
			log_doc.is_unclaimed = 0
			log_doc.flags.ignore_permissions = True
			log_doc.save()

	# 2. 重新计算该成员过去 14 天的缺勤状态
	from dev_workbench.services.absence_service import recalculate_member_absence_after_claim

	recalc_result = recalculate_member_absence_after_claim(member_id, past_days=14)

	return {
		"status": "success",
		"message": f"已成功将 Git 身份 {identity_name} 关联至成员 {member_id}",
		"recalculated": recalc_result,
	}


@frappe.whitelist(methods=["POST"])
def add_git_identity(member_id, identity, identity_type="Email"):
	"""为成员手动添加并认领一个新的 Git 身份"""
	_check_manager_permission()

	if not frappe.db.exists("Project Member", member_id):
		frappe.throw(_("成员不存在"), frappe.DoesNotExistError)

	identity = (identity or "").strip()
	if not identity:
		frappe.throw(_("Git 身份标识不能为空"))

	if frappe.db.exists("Git Identity", identity):
		doc = frappe.get_doc("Git Identity", identity)
		doc.member = member_id
		doc.identity_type = identity_type
		doc.status = "已认领"
		doc.claimed_at = now_datetime()
		doc.claimed_by = frappe.session.user
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc(
			{
				"doctype": "Git Identity",
				"identity": identity,
				"identity_type": identity_type,
				"member": member_id,
				"status": "已认领",
				"claimed_at": now_datetime(),
				"claimed_by": frappe.session.user,
			}
		).insert(ignore_permissions=True)

	return {
		"status": "success",
		"message": f"已成功为成员添加并认领 Git 身份: {identity}",
	}
