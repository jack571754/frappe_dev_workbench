# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json
from collections import defaultdict

import frappe
from frappe import _

from dev_workbench.services.absence_service import check_absences, get_absence_list_by_date
from dev_workbench.services.ai_summary_service import generate_summary_for_activity_log
from dev_workbench.services.feishu_card_builder import build_daily_report_card
from dev_workbench.services.feishu_client import FeishuAPIError, FeishuClient
from dev_workbench.services.workday_service import get_previous_workdays


def get_default_report_date() -> str:
	"""获取默认日报目标日期（前一工作日）"""
	today = frappe.utils.nowdate()
	prev_workdays = get_previous_workdays(today, count=1, include_ref_date=False)
	return prev_workdays[0] if prev_workdays else today


def build_daily_report_payload(report_date: str | None = None) -> dict:
	"""
	聚合指定工作日 (默认前一工作日) 的活动日志、缺勤记录与未归属提交
	生成飞书交互卡片及日报结构化数据
	"""
	if not report_date:
		report_date = get_default_report_date()

	# 1. 查询当日全部分支活动日志
	logs = frappe.get_all(
		"Daily Activity Log",
		filters={"activity_date": report_date, "branch_scope": "all"},
		fields=[
			"name",
			"member",
			"member_name",
			"project",
			"commit_count",
			"lines_added",
			"lines_deleted",
			"total_lines",
			"file_count",
			"is_unclaimed",
			"summary",
			"raw_json",
		],
	)

	# 2. 统计未归属提交与按项目分组
	unclaimed_commits_count = 0
	project_groups = defaultdict(list)

	for l in logs:
		if l.is_unclaimed:
			unclaimed_commits_count += int(l.commit_count or 0)
			continue

		# 确保已生成 AI 摘要（若无则兜底生成）
		summary = l.summary
		if not summary or summary.startswith("生成失败"):
			try:
				summary = generate_summary_for_activity_log(l.name)
			except Exception:
				summary = f"完成 {l.commit_count} 次代码提交"

		proj_name = l.project or "未分配项目"
		project_groups[proj_name].append(
			{
				"log_name": l.name,
				"member_id": l.member,
				"member_name": l.member_name or l.member,
				"commit_count": int(l.commit_count or 0),
				"lines_added": int(l.lines_added or 0),
				"lines_deleted": int(l.lines_deleted or 0),
				"total_lines": int(l.total_lines or 0),
				"file_count": int(l.file_count or 0),
				"summary": summary,
			}
		)

	projects_data = []
	for p_name, members in project_groups.items():
		projects_data.append(
			{
				"project_name": p_name,
				"members": sorted(members, key=lambda x: x["commit_count"], reverse=True),
			}
		)

	# 3. 获取缺勤记录
	absences = get_absence_list_by_date(date=report_date, include_exempted=1)
	if not absences:
		# 尝试即时核查
		absences = check_absences(check_date=report_date, consecutive_count=2)

	# 4. 构建卡片
	card_json = build_daily_report_card(
		report_date=report_date,
		projects_data=projects_data,
		absences_data=absences,
		unclaimed_count=unclaimed_commits_count,
	)

	total_active_members = sum(len(p["members"]) for p in projects_data)
	total_commits = sum(sum(m["commit_count"] for m in p["members"]) for p in projects_data)
	absent_unexempted = len([a for a in absences if not a.get("is_exempted")])

	text_summary = (
		f"工作日 {report_date}：活跃成员 {total_active_members} 人，"
		f"提交 {total_commits} 次；缺勤待跟进 {absent_unexempted} 人；"
		f"未归属提交 {unclaimed_commits_count} 次"
	)

	return {
		"report_date": report_date,
		"card": card_json,
		"summary": text_summary,
		"projects_data": projects_data,
		"absences_data": absences,
		"unclaimed_count": unclaimed_commits_count,
	}


def send_daily_report(
	report_date: str | None = None,
	target_open_id: str | None = None,
	client: FeishuClient | None = None,
) -> dict:
	"""
	向管理者推送飞书日报交互卡片，并记录到 Daily Report 数据表中
	:param report_date: 目标日期（默认前一工作日）
	:param target_open_id: 指定接收者 open_id（若为空则推送给所有 is_manager=1 且有 open_id 的成员）
	:param client: FeishuClient 实例 (可选)
	:return: dict
	"""
	payload = build_daily_report_payload(report_date=report_date)
	actual_date = payload["report_date"]
	card = payload["card"]
	summary = payload["summary"]

	# 查找目标接收人 open_id
	recipients = []
	if target_open_id:
		recipients.append(target_open_id.strip())
	else:
		managers = frappe.get_all(
			"Project Member",
			filters={"is_active": 1, "is_manager": 1},
			fields=["name", "member_name", "open_id"],
		)
		for m in managers:
			if m.open_id:
				recipients.append(m.open_id.strip())

	feishu_cli = client or FeishuClient()
	sent_message_ids = []
	errors = []

	if not recipients:
		# 无有效接收人，仍生成/保存 Daily Report 供归档查看
		frappe.logger("dev_workbench").warning(
			f"未能找到具有 open_id 的管理者接收人，日报仅存档: {actual_date}"
		)
		save_daily_report_record(
			report_date=actual_date,
			status="Draft",
			message_id="",
			summary=summary,
			content=json.dumps(card, ensure_ascii=False, indent=2),
		)
		return {
			"status": "warning",
			"message": "未配置管理者 open_id，已保存日报草稿记录",
			"report_date": actual_date,
			"summary": summary,
			"sent_count": 0,
			"errors": ["未找到具有有效 open_id 的管理者接收方"],
		}

	for r_id in recipients:
		try:
			res = feishu_cli.send_interactive_card(
				receive_id=r_id, card_content=card, receive_id_type="open_id"
			)
			msg_id = res.get("message_id") or ""
			if msg_id:
				sent_message_ids.append(msg_id)
		except Exception as e:
			err_msg = f"发送飞书日报给 {r_id} 失败: {e}"
			frappe.log_error(title="飞书日报推送失败", message=frappe.get_traceback())
			errors.append(err_msg)

	status = "Sent" if sent_message_ids else "Failed"
	combined_msg_id = ",".join(sent_message_ids)[:140]

	save_daily_report_record(
		report_date=actual_date,
		status=status,
		message_id=combined_msg_id,
		summary=summary,
		content=json.dumps(card, ensure_ascii=False, indent=2),
	)

	return {
		"status": "success" if status == "Sent" else "failed",
		"report_date": actual_date,
		"sent_count": len(sent_message_ids),
		"failed_count": len(errors),
		"message_ids": sent_message_ids,
		"errors": errors,
		"summary": summary,
	}


def save_daily_report_record(
	report_date: str,
	status: str,
	message_id: str,
	summary: str,
	content: str,
):
	"""保存或更新 Daily Report 记录"""
	existing = frappe.get_all(
		"Daily Report",
		filters={"report_date": report_date},
		fields=["name"],
		limit=1,
	)

	if existing:
		report_doc = frappe.get_doc("Daily Report", existing[0].name)
	else:
		report_doc = frappe.new_doc("Daily Report")
		report_doc.report_date = report_date

	report_doc.push_time = frappe.utils.now_datetime()
	report_doc.status = status
	if message_id:
		report_doc.message_id = message_id[:140]
	report_doc.summary = summary
	report_doc.content = content
	report_doc.flags.ignore_permissions = True
	report_doc.save()
	frappe.db.commit()
	return report_doc.name
