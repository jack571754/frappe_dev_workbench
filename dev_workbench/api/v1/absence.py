# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from dev_workbench.permissions import require_manager as verify_manager_permission
from dev_workbench.services.absence_service import check_absences, get_absence_list_by_date


@frappe.whitelist(methods=["GET"])
def get_absence_list(date=None, include_exempted=1, project=None):
	"""
	获取指定日期的缺勤成员列表（连续 2 工作日无提交）
	:param date: 检测目标日期 (YYYY-MM-DD)，默认当天
	:param include_exempted: 是否包含已请假豁免的成员 (1 或 0)
	:param project: 项目过滤 (可选)
	"""
	verify_manager_permission()
	if include_exempted is not None:
		include_exemp = bool(int(include_exempted))
	else:
		include_exemp = True

	list_data = get_absence_list_by_date(date_str=date, include_exempted=include_exemp)

	if project:
		# 筛选属于该项目的成员（根据近期活动或成员的项目所属）
		proj_members = frappe.get_all(
			"Daily Activity Log",
			filters={"project": project},
			pluck="member",
			distinct=True,
		)
		list_data = [item for item in list_data if item.get("member_id") in proj_members]

	return list_data


@frappe.whitelist(methods=["POST"])
def trigger_absence_check(date=None, consecutive_count=2, branch_scope="all"):
	"""
	手动触发一次缺勤检测并生成/更新 Absence Record
	"""
	verify_manager_permission()
	records = check_absences(
		check_date=date,
		consecutive_count=int(consecutive_count or 2),
		branch_scope=branch_scope,
	)
	return {
		"status": "success",
		"message": f"缺勤检测完成，共发现 {len(records)} 位成员连续无提交",
		"check_date": date or frappe.utils.nowdate(),
		"total_absences": len(records),
		"records": records,
	}


@frappe.whitelist(methods=["POST"])
def grant_exemption(member_id=None, start_date=None, end_date=None, reason=None):
	"""
	为指定成员快速添加请假豁免记录，并立即重算缺勤状态
	"""
	verify_manager_permission()
	if not member_id or not start_date or not end_date:
		frappe.throw(_("缺少必要参数: member_id, start_date, end_date"))

	exemp = frappe.new_doc("Absence Exemption")
	exemp.member = member_id
	exemp.start_date = start_date
	exemp.end_date = end_date
	exemp.reason = reason or "工作台手动标记请假豁免"
	exemp.is_active = 1
	exemp.flags.ignore_permissions = True
	exemp.insert()

	# 重算缺勤状态
	check_absences(check_date=end_date)

	return {
		"status": "success",
		"message": _("请假豁免标记成功"),
		"name": exemp.name,
	}
