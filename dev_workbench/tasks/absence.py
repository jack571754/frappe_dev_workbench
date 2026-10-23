# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _

from dev_workbench.services.absence_service import (
	check_absences,
	get_absence_list_by_date,
)
from dev_workbench.services.workday_service import (
	get_previous_workdays,
	is_workday,
	to_date_obj,
)


def check_absence(check_date=None, consecutive_count: int = 2, branch_scope="all") -> dict:
	"""
	定时任务：工作日缺勤检测
	执行频率：每个工作日晚上（如 18:00 / 21:00 由 Frappe Scheduler 调用）

	功能规范：
	1. 遍历所有 Project Member
	2. 检查过去 2 个工作日 (consecutive_count) 的 Daily Activity Log
	3. 检查并应用 Absence Exemption 请假豁免规则
	4. 生成或更新 Absence Record 缺勤记录（标记"待跟进"或"已豁免"）
	5. 容错处理：单个成员检查异常不中断其他成员
	6. 记录时间戳并在系统日志中持久化缺勤成员清单
	"""
	logger = frappe.logger("dev_workbench")
	now_str = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	if not check_date:
		check_date = frappe.utils.nowdate()

	check_date_obj = to_date_obj(check_date)
	check_date_str = check_date_obj.strftime("%Y-%m-%d")

	logger.info(f"[Scheduled Task] 开始执行缺勤检测任务: 日期={check_date_str}, 时间={now_str}")

	# 计算核查工作日
	if is_workday(check_date_obj):
		workdays = get_previous_workdays(check_date_obj, count=consecutive_count, include_ref_date=True)
	else:
		workdays = get_previous_workdays(check_date_obj, count=consecutive_count, include_ref_date=False)

	if not workdays:
		logger.info(f"日期 {check_date_str} 无有效工作日参考序列，跳过缺勤检测")
		return {
			"status": "skipped",
			"message": "无有效工作日序列",
			"check_date": check_date_str,
			"absences": [],
		}

	# 查询所有激活成员
	members = frappe.get_all(
		"Project Member",
		filters={"is_active": 1},
		fields=["name", "member_name", "email", "department"],
	)

	absence_records = []
	failed_members = []

	for member in members:
		try:
			# 检查在核查工作日内是否有代码提交
			filters = {
				"member": member.name,
				"activity_date": ["in", workdays],
				"commit_count": [">", 0],
			}
			if branch_scope and branch_scope != "all":
				filters["branch_scope"] = branch_scope

			has_commits = frappe.db.exists("Daily Activity Log", filters)

			if has_commits:
				# 若此前已生成该日的缺勤记录，则自动撤回/清理
				existing_rec = frappe.db.get_value(
					"Absence Record",
					{"member": member.name, "check_date": check_date_str},
					"name",
				)
				if existing_rec:
					frappe.delete_doc("Absence Record", existing_rec, ignore_permissions=True)
				continue

			# 连续工作日无提交，核查请假豁免 (Absence Exemption)
			exemptions = frappe.get_all(
				"Absence Exemption",
				filters={"member": member.name, "is_active": 1},
				fields=["name", "start_date", "end_date", "reason"],
			)

			is_exempted = 0
			exemption_reason = None

			for exemp in exemptions:
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

			# 查询最近一次有效提交
			last_activity = frappe.get_all(
				"Daily Activity Log",
				filters={"member": member.name, "commit_count": [">", 0]},
				fields=["activity_date", "project"],
				order_by="activity_date desc",
				limit=1,
			)
			last_commit_date = last_activity[0].activity_date if last_activity else None
			last_commit_repo = last_activity[0].project if last_activity else None

			# 保存或更新 Absence Record
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

		except Exception as e:
			failed_members.append({"member": member.name, "error": str(e)})
			logger.error(f"缺勤检测处理成员 {member.name} 发生异常: {e}")
			frappe.log_error(title=f"缺勤检测异常 ({member.name})", message=frappe.get_traceback())

	frappe.db.commit()

	pending_list = [a["member_name"] for a in absence_records if not a["is_exempted"]]
	exempted_list = [a["member_name"] for a in absence_records if a["is_exempted"]]

	summary_msg = (
		f"缺勤检测完成: 核查成员 {len(members)} 人, "
		f"连续 {len(workdays)} 工作日无提交 {len(absence_records)} 人 "
		f"(待跟进: {len(pending_list)} 人 [{', '.join(pending_list) or '无'}], "
		f"已豁免: {len(exempted_list)} 人 [{', '.join(exempted_list) or '无'}])"
	)

	logger.info(f"[Scheduled Task] {summary_msg}")

	return {
		"status": "success",
		"message": summary_msg,
		"check_date": check_date_str,
		"timestamp": now_str,
		"total_checked": len(members),
		"absent_count": len(absence_records),
		"pending_count": len(pending_list),
		"exempted_count": len(exempted_list),
		"pending_members": pending_list,
		"exempted_members": exempted_list,
		"absences": absence_records,
		"failed_members": failed_members,
	}
