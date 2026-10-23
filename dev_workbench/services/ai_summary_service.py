# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from dev_workbench.services.ai_client import (
	AIServiceError,
	OpenAIClient,
	build_summary_prompt,
	clean_and_truncate_summary,
	get_ai_settings,
)


def generate_summary_for_activity_log(log_doc_or_name, client=None, force=False):
	"""
	为单条 Daily Activity Log 记录生成 AI 工作摘要
	结果保存至 DailyActivityLog.summary 字段中
	:param log_doc_or_name: Daily Activity Log doc 实例或 docname 字符串
	:param client: OpenAIClient 实例 (可选，默认根据系统设置实例化)
	:param force: 是否强制重新生成（忽略缓存）
	:return: summary 字符串
	"""
	if isinstance(log_doc_or_name, str):
		log_doc = frappe.get_doc("Daily Activity Log", log_doc_or_name)
	else:
		log_doc = log_doc_or_name

	# 1. 摘要缓存检查：已生成的摘要不重复调用 API (非 force 且非 "生成失败")
	if log_doc.summary and not force:
		if not log_doc.summary.startswith("生成失败"):
			return log_doc.summary

	# 2. 检查提交数据
	commits = []
	if log_doc.raw_json:
		try:
			parsed = json.loads(log_doc.raw_json)
			if isinstance(parsed, list):
				commits = parsed
		except Exception:
			pass

	if not commits or int(log_doc.commit_count or 0) == 0:
		empty_summary = "今日无有效代码提交"
		frappe.db.set_value("Daily Activity Log", log_doc.name, "summary", empty_summary)
		log_doc.summary = empty_summary
		return empty_summary

	# 3. 检查 AI 配置
	settings = get_ai_settings()
	if not settings.get("ai_enabled"):
		fallback_summary = f"完成 {log_doc.commit_count} 次代码提交，涉及 {log_doc.file_count or len(commits)} 个文件变更 (AI未启用)"
		frappe.db.set_value("Daily Activity Log", log_doc.name, "summary", fallback_summary)
		log_doc.summary = fallback_summary
		return fallback_summary

	if not settings.get("ai_api_key"):
		fallback_summary = "生成失败: 未配置 AI 模型 API Key"
		frappe.db.set_value("Daily Activity Log", log_doc.name, "summary", fallback_summary)
		log_doc.summary = fallback_summary
		return fallback_summary

	# 4. 构建 Prompt（严禁发送 diff，仅提交信息 + 文件列表）
	messages = build_summary_prompt(commits)

	# 5. 调用模型接口生成摘要并处理错误
	ai_client = client or OpenAIClient()
	try:
		raw_summary = ai_client.generate_chat_completion(messages)
		summary = clean_and_truncate_summary(raw_summary, max_length=100)
		if not summary:
			summary = "完成日常代码开发与提交"
	except Exception:
		# 记录错误到 Frappe 错误日志，不阻塞流程，标记为生成失败
		error_title = f"AI 摘要生成失败 [{log_doc.name}]"
		frappe.log_error(title=error_title, message=frappe.get_traceback())
		summary = "生成失败"

	# 6. 持久化存储结果到 DailyActivityLog
	frappe.db.set_value("Daily Activity Log", log_doc.name, "summary", summary)
	log_doc.summary = summary
	return summary


def generate_daily_summaries_for_date(date=None, force=False, client=None):
	"""
	批量为指定日期的所有活动日志生成 AI 摘要
	:param date: YYYY-MM-DD，默认今天
	:param force: 是否强制重算
	:param client: 可选客户端
	:return: 处理的日志数量 dict {"total": N, "success": N, "failed": N}
	"""
	if not date:
		date = frappe.utils.nowdate()

	filters = {"activity_date": date}
	if not force:
		# 仅处理尚未生成摘要或先前失败的记录
		logs = frappe.get_all(
			"Daily Activity Log",
			filters=filters,
			fields=["name", "summary", "commit_count", "raw_json"],
		)
		target_logs = [l for l in logs if not l.summary or l.summary.startswith("生成失败")]
	else:
		target_logs = frappe.get_all(
			"Daily Activity Log",
			filters=filters,
			fields=["name", "summary", "commit_count", "raw_json"],
		)

	ai_client = client or OpenAIClient()
	success_count = 0
	failed_count = 0

	for item in target_logs:
		try:
			summary = generate_summary_for_activity_log(item.name, client=ai_client, force=force)
			if summary and not summary.startswith("生成失败"):
				success_count += 1
			else:
				failed_count += 1
		except Exception as e:
			frappe.log_error(title=f"批量生成 AI 摘要失败 [{item.name}]", message=str(e))
			failed_count += 1

	frappe.db.commit()
	return {
		"total": len(target_logs),
		"success": success_count,
		"failed": failed_count,
	}


def generate_daily_summaries_background(date=None, force=False):
	"""
	后台异步队列调用的入口函数
	通过 frappe.enqueue 触发，不阻塞主流程
	"""
	try:
		frappe.logger("dev_workbench").info(f"开始后台异步生成 {date} 的 AI 代码活动摘要...")
		result = generate_daily_summaries_for_date(date=date, force=force)
		frappe.logger("dev_workbench").info(f"后台异步生成完成: {result}")
		return result
	except Exception as e:
		frappe.log_error(title="后台生成 AI 摘要任务异常", message=frappe.get_traceback())
		return {"error": str(e)}


def enqueue_summary_generation(date=None, force=False):
	"""
	将生成任务推入后台队列执行
	"""
	if not date:
		date = frappe.utils.nowdate()

	job = frappe.enqueue(
		"dev_workbench.services.ai_summary_service.generate_daily_summaries_background",
		queue="default",
		timeout=300,
		is_async=True,
		date=date,
		force=force,
	)
	return {"job_id": job.id if hasattr(job, "id") else "enqueued", "date": date}
