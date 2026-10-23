# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from dev_workbench.permissions import require_manager as verify_manager_permission
from dev_workbench.services.feishu_report_service import (
	build_daily_report_payload,
	send_daily_report,
)


@frappe.whitelist(methods=["POST"])
def test_feishu_report(date=None, open_id=None):
	"""
	管理者手动推送一条测试日报消息到飞书。
	:param date: 目标工作日期 (YYYY-MM-DD)，默认前一工作日
	:param open_id: 指定接收人 open_id (默认推给当前用户或所有管理者)
	"""
	verify_manager_permission()

	# 支持从 JSON 请求体解析参数
	if isinstance(frappe.request.data, (bytes, str)) and frappe.request.data:
		try:
			parsed = json.loads(frappe.request.data)
			if isinstance(parsed, dict):
				date = date or parsed.get("date")
				open_id = open_id or parsed.get("open_id")
		except Exception:
			pass

	# 若未指定 open_id，尝试查找当前用户的 open_id
	if not open_id:
		current_user_email = frappe.session.user
		if current_user_email and current_user_email != "Administrator":
			user_open_id = frappe.db.get_value(
				"Project Member",
				{"email": current_user_email, "is_active": 1},
				"open_id",
			)
			if user_open_id:
				open_id = user_open_id

	res = send_daily_report(report_date=date, target_open_id=open_id)
	return res


@frappe.whitelist(methods=["GET"])
def preview_daily_report(date=None):
	"""
	预览指定日期的日报卡片结构与汇总数据。
	"""
	verify_manager_permission()
	payload = build_daily_report_payload(report_date=date)
	return payload
