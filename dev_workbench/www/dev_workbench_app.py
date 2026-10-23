# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from dev_workbench.permissions import has_manager_access


def get_context(context):
	"""为 Dev Workbench SPA 提供上下文数据与权限拦截"""
	context.no_cache = 1

	# 1. 登录检查
	if frappe.session.user == "Guest":
		req_path = (
			getattr(frappe.request, "path", None) if getattr(frappe, "request", None) else "/dev-workbench"
		)
		redirect_url = f"/login?redirect-to={req_path or '/dev-workbench'}"
		frappe.local.flags.redirect_location = redirect_url
		raise frappe.Redirect

	user = frappe.session.user
	roles = frappe.get_roles(user)
	is_manager = has_manager_access(user)
	if not is_manager:
		# 如果不是管理者，抛出无权限提示或重定向
		frappe.throw(
			_("您没有访问研发工作台的权限。只有飞书通讯录中被标记为'管理者'的人员可以访问。"),
			frappe.PermissionError,
		)

	# 3. 注入 CSRF Token 与 Boot 信息
	try:
		csrf_token = frappe.sessions.get_csrf_token()
	except Exception:
		csrf_token = getattr(frappe.local, "csrf_token", "") or "test_csrf_token"
	context.csrf_token = csrf_token

	boot_info = {
		"user": user,
		"user_fullname": frappe.utils.get_fullname(user),
		"user_image": frappe.db.get_value("User", user, "user_image"),
		"csrf_token": csrf_token,
		"roles": roles,
		"is_manager": is_manager,
		"sitename": frappe.local.site,
	}

	context.boot = boot_info
	context.title = "研发工作台"
