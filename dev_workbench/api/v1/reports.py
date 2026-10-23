# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from dev_workbench.permissions import require_manager as verify_manager_permission
from dev_workbench.services.feishu_report_service import send_daily_report


@frappe.whitelist(methods=["GET"])
def get_reports_list(from_date=None, to_date=None, limit=100):
	"""
	获取历史日报归档列表
	通过 Frappe method API 获取日报列表。
	"""
	verify_manager_permission()

	from_date = from_date or frappe.form_dict.get("from_date")
	to_date = to_date or frappe.form_dict.get("to_date")
	limit = int(limit or frappe.form_dict.get("limit") or 100)

	filters = {}
	if from_date and to_date:
		filters["report_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["report_date"] = [">=", from_date]
	elif to_date:
		filters["report_date"] = ["<=", to_date]

	reports = frappe.get_all(
		"Daily Report",
		filters=filters,
		fields=[
			"name",
			"report_date",
			"push_time",
			"status",
			"message_id",
			"summary",
		],
		order_by="report_date desc",
		limit=limit,
	)

	for r in reports:
		if r.get("report_date"):
			r["report_date"] = str(r["report_date"])
		if r.get("push_time"):
			r["push_time"] = str(r["push_time"])

	return reports


@frappe.whitelist(methods=["GET"])
def get_report_detail(report_id=None):
	"""
	获取单个日报详情
	通过 Frappe method API 获取日报详情。
	report_id 可以为 docname (如 RPT-2026-10-13) 或 report_date (如 2026-10-13)
	"""
	verify_manager_permission()

	report_id = report_id or frappe.form_dict.get("report_id")
	if not report_id:
		frappe.throw(_("缺少 report_id 参数"), frappe.ValidationError)

	doc = None
	if frappe.db.exists("Daily Report", report_id):
		doc = frappe.get_doc("Daily Report", report_id)
	else:
		existing = frappe.get_all("Daily Report", filters={"report_date": report_id}, limit=1)
		if existing:
			doc = frappe.get_doc("Daily Report", existing[0].name)

	if not doc:
		frappe.throw(_("未找到指定的日报记录: {0}").format(report_id), frappe.DoesNotExistError)

	parsed_card = None
	if doc.content:
		try:
			parsed_card = json.loads(doc.content)
		except Exception:
			parsed_card = None

	return {
		"name": doc.name,
		"report_date": str(doc.report_date),
		"push_time": str(doc.push_time) if doc.push_time else None,
		"status": doc.status,
		"message_id": doc.message_id,
		"summary": doc.summary,
		"content": doc.content,
		"card": parsed_card,
	}


@frappe.whitelist(methods=["POST"])
def resend_report(report_id=None):
	"""
	重新推送指定日报消息到飞书
	通过 Frappe method API 重新推送日报。
	"""
	verify_manager_permission()

	report_id = report_id or frappe.form_dict.get("report_id")
	if not report_id:
		frappe.throw(_("缺少 report_id 参数"), frappe.ValidationError)

	doc = None
	if frappe.db.exists("Daily Report", report_id):
		doc = frappe.get_doc("Daily Report", report_id)
	else:
		existing = frappe.get_all("Daily Report", filters={"report_date": report_id}, limit=1)
		if existing:
			doc = frappe.get_doc("Daily Report", existing[0].name)

	if not doc:
		frappe.throw(_("未找到指定的日报记录: {0}").format(report_id), frappe.DoesNotExistError)

	target_date = str(doc.report_date)

	# 调用飞书推送
	send_res = send_daily_report(report_date=target_date)

	# 重新读取最新状态
	updated_doc = frappe.get_doc("Daily Report", doc.name)

	return {
		"status": send_res.get("status"),
		"report_id": updated_doc.name,
		"report_date": str(updated_doc.report_date),
		"push_status": updated_doc.status,
		"message_id": updated_doc.message_id,
		"push_time": str(updated_doc.push_time) if updated_doc.push_time else None,
		"sent_count": send_res.get("sent_count", 0),
		"errors": send_res.get("errors", []),
		"send_result": send_res,
	}
