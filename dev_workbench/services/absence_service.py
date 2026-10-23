# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe import _

from dev_workbench.services.workday_service import (
	get_previous_workdays,
	get_workdays_between,
	is_workday,
	to_date_obj,
)


def check_absences(check_date=None, consecutive_count: int = 2, branch_scope="all"):
	"""
	检测所有活跃成员在指定日期的连续无提交缺勤情况：
	- 识别过去 consecutive_count 个工作日（默认为连续 2 个工作日）
	- 检查 DailyActivityLog 是否连续无任何提交
	- 检查 AbsenceExemption 表是否有请假豁免记录
	- 记录至 Absence Record 表
	"""
	if not check_date:
		check_date = frappe.utils.nowdate()

	check_date_obj = to_date_obj(check_date)
	check_date_str = check_date_obj.strftime("%Y-%m-%d")

	# 计算需要核查的连续工作日
	if is_workday(check_date_obj):
		workdays = get_previous_workdays(check_date_obj, count=consecutive_count, include_ref_date=True)
	else:
		workdays = get_previous_workdays(check_date_obj, count=consecutive_count, include_ref_date=False)

	if not workdays:
		return []

	# 查询所有在职活跃成员
	members = frappe.get_all(
		"Project Member",
		filters={"is_active": 1},
		fields=["name", "member_name", "email", "department"],
	)

	absence_records = []

	for member in members:
		# 1. 检查该成员在核查工作日内是否有任何提交
		filters = {
			"member": member.name,
			"activity_date": ["in", workdays],
			"commit_count": [">", 0],
		}
		if branch_scope and branch_scope != "all":
			filters["branch_scope"] = branch_scope

		has_commits = frappe.db.exists("Daily Activity Log", filters)

		if has_commits:
			# 有提交，如果此前已生成过该检测日期的待跟进缺勤记录，则自动撤销/清理
			existing_rec = frappe.db.get_value(
				"Absence Record",
				{"member": member.name, "check_date": check_date_str},
				"name",
			)
			if existing_rec:
				frappe.delete_doc("Absence Record", existing_rec, ignore_permissions=True)
			continue

		# 2. 连续工作日无提交，核查请假豁免 (Absence Exemption)
		exemptions = frappe.get_all(
			"Absence Exemption",
			filters={"member": member.name, "is_active": 1},
			fields=["name", "start_date", "end_date", "reason"],
		)

		is_exempted = 0
		exemption_reason = None

		for exemp in exemptions:
			# 只要豁免区间覆盖了核查工作日中的任一天，即算作已请假豁免
			exemp_start = to_date_obj(exemp.start_date)
			exemp_end = to_date_obj(exemp.end_date)
			for d_str in workdays:
				d_obj = to_date_obj(d_str)
				if exemp_start <= d_obj <= exemp_end:
					is_exempted = 1
					exemption_reason = exemp.reason or "请假已备案"
					break
			if is_exempted:
				break

		# 3. 查询最近一次提交时间与项目
		last_activity = frappe.get_all(
			"Daily Activity Log",
			filters={"member": member.name, "commit_count": [">", 0]},
			fields=["activity_date", "project"],
			order_by="activity_date desc",
			limit=1,
		)
		last_commit_date = last_activity[0].activity_date if last_activity else None
		last_commit_repo = last_activity[0].project if last_activity else None

		# 4. 创建或更新 Absence Record
		existing_record_name = frappe.db.get_value(
			"Absence Record",
			{"member": member.name, "check_date": check_date_str},
			"name",
		)

		if existing_record_name:
			doc = frappe.get_doc("Absence Record", existing_record_name)
		else:
			doc = frappe.new_doc("Absence Record")
			doc.member = member.name
			doc.check_date = check_date_str

		doc.member_name = member.member_name
		doc.consecutive_workdays = len(workdays)
		doc.absent_dates = ", ".join(workdays)
		doc.is_exempted = is_exempted
		doc.exemption_reason = exemption_reason
		doc.status = "已豁免" if is_exempted else "待跟进"
		doc.last_commit_date = last_commit_date
		doc.last_commit_repo = last_commit_repo

		doc.flags.ignore_permissions = True
		doc.save()

		absence_records.append(
			{
				"name": doc.name,
				"member_id": member.name,
				"member_name": member.member_name,
				"email": member.email,
				"check_date": check_date_str,
				"consecutive_workdays": len(workdays),
				"absent_dates": workdays,
				"is_exempted": is_exempted,
				"exemption_reason": exemption_reason,
				"status": doc.status,
				"last_commit_date": str(last_commit_date) if last_commit_date else None,
				"last_commit_repo": last_commit_repo,
			}
		)

	frappe.db.commit()
	return absence_records


def get_absence_list_by_date(date_str=None, date=None, include_exempted: bool = True):
	"""
	获取指定日期的缺勤记录列表
	"""
	target_date = date_str or date
	if not target_date:
		target_date = frappe.utils.nowdate()

	clean_date = to_date_obj(target_date).strftime("%Y-%m-%d")

	# 若当天尚无缺勤检测记录，自动触发一次检测
	existing_count = frappe.db.count("Absence Record", {"check_date": clean_date})
	if existing_count == 0:
		check_absences(check_date=clean_date)

	filters = {"check_date": clean_date}
	if not include_exempted:
		filters["is_exempted"] = 0

	records = frappe.get_all(
		"Absence Record",
		filters=filters,
		fields=[
			"name",
			"member",
			"member_name",
			"check_date",
			"consecutive_workdays",
			"absent_dates",
			"status",
			"is_exempted",
			"exemption_reason",
			"last_commit_date",
			"last_commit_repo",
			"notified_feishu",
		],
		order_by="is_exempted asc, member_name asc",
	)

	result = []
	for r in records:
		member_email = frappe.db.get_value("Project Member", r.member, "email") or ""
		dates_list = [d.strip() for d in (r.absent_dates or "").split(",") if d.strip()]
		result.append(
			{
				"name": r.name,
				"member_id": r.member,
				"member_name": r.member_name,
				"email": member_email,
				"check_date": str(r.check_date),
				"consecutive_workdays": r.consecutive_workdays,
				"absent_dates": dates_list,
				"is_exempted": r.is_exempted,
				"exemption_reason": r.exemption_reason,
				"status": r.status,
				"last_commit_date": str(r.last_commit_date) if r.last_commit_date else None,
				"last_commit_repo": r.last_commit_repo,
				"notified_feishu": r.notified_feishu,
			}
		)
	return result


def recalculate_member_absence_after_claim(member_id: str, past_days: int = 14):
	"""
	当管理者认领 Git 身份后，回溯重新评估并校正该成员过去 past_days 天的缺勤状态
	"""
	if not member_id:
		return {"recalculated_days": 0, "cleared_absences": 0}

	end_date = frappe.utils.getdate(frappe.utils.nowdate())
	start_date = end_date - timedelta(days=past_days)

	# 1. 查找此成员在过去 past_days 天内存在的缺勤记录
	existing_absences = frappe.get_all(
		"Absence Record",
		filters={
			"member": member_id,
			"check_date": ["between", [str(start_date), str(end_date)]],
		},
		fields=["name", "check_date", "absent_dates"],
	)

	cleared_count = 0
	for rec in existing_absences:
		dates = [d.strip() for d in (rec.absent_dates or "").split(",") if d.strip()]
		if not dates:
			continue

		# 检查该成员认领身份后在这些日期是否有提交
		commits_count = frappe.db.count(
			"Daily Activity Log",
			{
				"member": member_id,
				"activity_date": ["in", dates],
				"commit_count": [">", 0],
			},
		)

		if commits_count > 0:
			# 已有提交，撤销此误报的缺勤记录
			frappe.delete_doc("Absence Record", rec.name, ignore_permissions=True)
			cleared_count += 1

	frappe.db.commit()
	return {
		"member_id": member_id,
		"recalculated_days": past_days,
		"cleared_absences": cleared_count,
	}
