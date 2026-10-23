# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _

from dev_workbench.services.feishu_report_service import (
	get_default_report_date,
	send_daily_report,
)
from dev_workbench.services.workday_service import (
	get_previous_workdays,
	is_workday,
	to_date_obj,
)


def push_daily_report(report_date=None, force=False) -> dict:
	"""
	定时任务：每个工作日早上 9 点向研发管理者推送前一工作日的效能日报飞书交互卡片
	执行频率：每个工作日早晨 09:00 (cron: 0 9 * * 1-5 由 Frappe Scheduler 调用)

	功能规范：
	1. 工作日智能调度：若今日为周末或法定节假日（且未开启 force），自动跳过推送避免打扰管理者
	2. 确定前一工作日：自动排除周末和法定节假日，定位待汇总工作日
	3. 数据汇总与卡片构建：聚合活动日志、AI 单句摘要、缺勤告警、未归属提示、以及直达看板链接
	4. 飞书卡片推送：调用飞书应用机器人 API 推送给具有 is_manager=1 且有 open_id 的管理者
	5. 历史归档存储：将推送状态、推送时间、飞书 message_id、内容摘要与卡片 JSON 持久化至 Daily Report 表
	6. 错误处理与日志：推送异常记录到 Frappe 错误日志并返回状态
	"""
	logger = frappe.logger("dev_workbench")
	today_str = frappe.utils.nowdate()
	now_str = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	logger.info(f"[Scheduled Task] 开始执行飞书日报推送任务: 当前时间={now_str}, 今日={today_str}")

	# 1. 检查今日是否为工作日
	today_is_workday = is_workday(today_str)
	if not today_is_workday and not force:
		skip_msg = f"今日 ({today_str}) 为休息日或法定节假日，自动跳过早晨 09:00 飞书日报推送"
		logger.info(skip_msg)
		return {
			"status": "skipped",
			"message": skip_msg,
			"today": today_str,
			"target_date": None,
		}

	# 2. 确定前一工作日
	if not report_date:
		report_date = get_default_report_date()

	logger.info(f"目标汇总工作日: {report_date}")

	# 3. 执行推送并写入 Daily Report
	try:
		res = send_daily_report(report_date=report_date)
		summary = res.get("summary", "")
		sent_count = res.get("sent_count", 0)
		status = res.get("status", "unknown")

		log_msg = (
			f"飞书日报推送完成: 目标日期={report_date}, "
			f"推送状态={status}, 成功推送={sent_count} 人, "
			f"摘要={summary}"
		)
		logger.info(f"[Scheduled Task] {log_msg}")

		return {
			"status": status,
			"message": log_msg,
			"report_date": report_date,
			"timestamp": now_str,
			"sent_count": sent_count,
			"message_ids": res.get("message_ids", []),
			"summary": summary,
			"errors": res.get("errors", []),
			"details": res,
		}

	except Exception as e:
		err_msg = f"飞书日报定时推送发生异常 (目标日期 {report_date}): {e}"
		logger.error(err_msg)
		frappe.log_error(title=f"飞书日报定时推送异常 ({report_date})", message=frappe.get_traceback())
		return {
			"status": "failed",
			"message": err_msg,
			"report_date": report_date,
			"timestamp": now_str,
			"error": str(e),
		}
