# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe


def build_daily_report_card(
	report_date: str,
	projects_data: list,
	absences_data: list,
	unclaimed_count: int = 0,
	site_url: str | None = None,
) -> dict:
	"""
	构造飞书交互卡片消息 (Interactive Card)
	符合 Issue 08 规范：
	1. 顶部 Header：工作日期与效能简报标识
	2. 概览指标：总活跃人数、总提交次数、变更总代码行
	3. 按项目分栏：项目名称、成员活动（提交数、行数、文件数）与 AI 生成摘要
	4. 缺勤提醒分栏：连续 2 工作日无提交成员与豁免状态醒目标记
	5. 未归属提交提示：存在未关联成员提交时的认领警示
	6. 页面链接：跳转到工作台对应日期的看板详细页面
	"""
	if not site_url:
		try:
			site_url = frappe.utils.get_url()
		except Exception:
			site_url = "http://development.localhost"

	dashboard_url = f"{site_url.rstrip('/')}/dev-workbench/dashboard/daily-activity?date={report_date}"

	# 统计汇总指标
	total_active_members = set()
	total_commits = 0
	total_lines = 0

	for proj in projects_data:
		for mem in proj.get("members", []):
			total_active_members.add(mem.get("member_name") or mem.get("member_id"))
			total_commits += int(mem.get("commit_count") or 0)
			total_lines += int(mem.get("total_lines") or 0)

	elements = []

	# 1. 顶部工作日期与团队汇总
	overview_text = (
		f"📅 **工作日期**：{report_date}\n"
		f"👥 **活跃开发者**：{len(total_active_members)} 人  |  "
		f"📝 **代码提交**：{total_commits} 次  |  "
		f"📈 **代码变更**：{total_lines} 行"
	)
	elements.append(
		{
			"tag": "div",
			"text": {
				"tag": "lark_md",
				"content": overview_text,
			},
		}
	)
	elements.append({"tag": "hr"})

	# 2. 按项目分栏 (Projects Sections)
	if projects_data:
		elements.append(
			{
				"tag": "div",
				"text": {
					"tag": "lark_md",
					"content": "### 📦 项目研发动态",
				},
			}
		)

		for proj in projects_data:
			proj_name = proj.get("project_name") or "未分类项目"
			members = proj.get("members") or []
			if not members:
				continue

			lines = [f"**【{proj_name}】** ({len(members)}人活跃)"]
			for m in members:
				m_name = m.get("member_name") or m.get("member_id") or "开发者"
				c_count = m.get("commit_count", 0)
				t_lines = m.get("total_lines", 0)
				f_count = m.get("file_count", 0)
				summary = m.get("summary") or "常规代码开发与维护"

				lines.append(
					f"• **{m_name}**：提交 **{c_count}** 次，变更 **{t_lines}** 行，涉及 **{f_count}** 个文件\n"
					f"  > 💡 *AI 摘要：{summary}*"
				)

			elements.append(
				{
					"tag": "div",
					"text": {
						"tag": "lark_md",
						"content": "\n".join(lines),
					},
				}
			)
	else:
		elements.append(
			{
				"tag": "div",
				"text": {
					"tag": "lark_md",
					"content": "ℹ️ 当日暂无项目代码提交记录",
				},
			}
		)

	elements.append({"tag": "hr"})

	# 3. 缺勤提醒分栏 (Absence Section - 醒目标记)
	if absences_data:
		absence_lines = ["### ⚠️ 缺勤提醒 (连续 2 工作日无提交)"]
		for ab in absences_data:
			m_name = ab.get("member_name") or ab.get("member_id") or "成员"
			days = ab.get("consecutive_workdays", 2)
			is_exempted = ab.get("is_exempted")
			reason = ab.get("exemption_reason")

			if is_exempted:
				absence_lines.append(
					f"• **{m_name}**：已连续 {days} 工作日无提交 (🔵 已请假豁免: {reason or '无说明'})"
				)
			else:
				absence_lines.append(
					f"• **{m_name}**：已连续 **{days}** 工作日无提交 (🔴 **待跟进**) - 请管理者关注"
				)

		elements.append(
			{
				"tag": "div",
				"text": {
					"tag": "lark_md",
					"content": "\n".join(absence_lines),
				},
			}
		)
	else:
		elements.append(
			{
				"tag": "div",
				"text": {
					"tag": "lark_md",
					"content": "✅ **全员正常出勤**：过去 2 个工作日所有激活成员均有正常提交记录",
				},
			}
		)

	# 4. 未归属提交数量提示 (Unclaimed Hint)
	if unclaimed_count > 0:
		elements.append({"tag": "hr"})
		elements.append(
			{
				"tag": "div",
				"text": {
					"tag": "lark_md",
					"content": f"❓ **未归属提交提示**：昨日存在 **{unclaimed_count}** 条未归属提交，请前往工作台及时认领 Git 身份。",
				},
			}
		)

	elements.append({"tag": "hr"})

	# 5. 详细看板页面跳转按钮
	elements.append(
		{
			"tag": "action",
			"actions": [
				{
					"tag": "button",
					"text": {
						"tag": "plain_text",
						"content": "👉 打开研发工作台看板查看详情",
					},
					"type": "primary",
					"url": dashboard_url,
				}
			],
		}
	)

	card = {
		"config": {
			"wide_screen_mode": True,
		},
		"header": {
			"title": {
				"tag": "plain_text",
				"content": f"📊 研发效能日报 ({report_date})",
			},
			"template": "blue" if not absences_data else "carmine",
		},
		"elements": elements,
	}

	return card
