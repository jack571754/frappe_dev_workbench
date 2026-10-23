# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import calendar
import json
from collections import defaultdict
from datetime import date, datetime, timedelta

import frappe

from dev_workbench.api.v1.activity import _parse_multi_values
from dev_workbench.services.workday_service import to_date_obj


def get_monday(dt: date) -> date:
	"""获取日期所在周的周一"""
	return dt - timedelta(days=dt.weekday())


def get_activity_trend(
	project_id: str = "all",
	scope: str = "all",
	member_id: str | None = None,
	ref_date: str | None = None,
	interval: str = "week",
	days: int = 30,
	repository: str | None = None,
) -> dict:
	"""
	计算项目或全队代码提交与行数活跃度趋势数据
	支持按天 (day)、按周 (week)、按月 (month) 维度统计与聚合
	同时支持项目附带代码仓库名称展示与单个代码仓库筛选

	:param project_id: 项目 ID 或 'all' (全部项目)
	:param scope: 分支统计范围 ('all' 或 'default')，默认 'all' (全部分支)
	:param member_id: 可选成员 ID，用于筛选个人趋势
	:param ref_date: 基准日期 (默认今天)
	:param interval: 聚合时间粒度：'day' (按天), 'week' (按周，默认), 'month' (按月)
	:param days: 当 interval='day' 时的天数范围（默认 30 天）
	:param repository: 可选代码仓库名称，用于筛选特定仓库
	:return: dict 包含周期标签、系列数据、均值基准线与度量汇总
	"""
	# 1. 规范化参数
	scope_str = (scope or "all").lower()
	if scope_str in ("default", "仅默认分支", "默认"):
		norm_scope = "default"
	else:
		norm_scope = "all"

	interval = (interval or "week").lower()
	if interval not in ("day", "week", "month"):
		interval = "week"

	ref_date_obj = to_date_obj(ref_date) if ref_date else date.today()

	intervals = []
	periods_labels = []
	periods_short = []

	# 2. 根据时间粒度生成统计区间
	if interval == "day":
		# 按天统计：最近 N 天（默认 30 天，从旧到新）
		try:
			num_days = max(7, min(int(days or 30), 90))
		except ValueError, TypeError:
			num_days = 30

		weekdays_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
		for i in range(num_days - 1, -1, -1):
			day = ref_date_obj - timedelta(days=i)
			intervals.append((day, day))
			short_lbl = day.strftime("%m/%d")
			full_lbl = f"{day.strftime('%Y-%m-%d')} ({weekdays_cn[day.weekday()]})"
			periods_short.append(short_lbl)
			periods_labels.append(full_lbl)

	elif interval == "month":
		# 按月统计：过去 12 个月（从旧到新）
		curr_y = ref_date_obj.year
		curr_m = ref_date_obj.month
		for i in range(11, -1, -1):
			total_m = curr_y * 12 + curr_m - 1 - i
			target_year = total_m // 12
			target_month = total_m % 12 + 1
			m_start = date(target_year, target_month, 1)
			last_day = calendar.monthrange(target_year, target_month)[1]
			m_end = date(target_year, target_month, last_day)

			intervals.append((m_start, m_end))
			short_lbl = f"{target_year % 100:02d}/{target_month:02d}"
			full_lbl = f"{target_year}年{target_month:02d}月"
			periods_short.append(short_lbl)
			periods_labels.append(full_lbl)

	else:
		# 默认：按周统计（过去 12 周，从旧到新）
		current_monday = get_monday(ref_date_obj)
		for i in range(11, -1, -1):
			w_start = current_monday - timedelta(weeks=i)
			w_end = w_start + timedelta(days=6)
			w_num = w_start.isocalendar()[1]
			short_lbl = w_start.strftime("%m/%d")
			full_lbl = f"W{w_num:02d} ({short_lbl})"

			intervals.append((w_start, w_end))
			periods_short.append(short_lbl)
			periods_labels.append(full_lbl)

	num_slots = len(intervals)
	earliest_date = intervals[0][0].strftime("%Y-%m-%d")
	latest_date = intervals[-1][1].strftime("%Y-%m-%d")

	# 查询项目与代码仓库的关联映射
	repo_items = frappe.get_all("Project Repository Item", fields=["parent", "repository"])
	project_repos_map = defaultdict(list)
	for it in repo_items:
		if it.repository and it.repository not in project_repos_map[it.parent]:
			project_repos_map[it.parent].append(it.repository)

	# 3. 构造数据库查询条件
	filters = {
		"activity_date": ["between", [earliest_date, latest_date]],
		"branch_scope": norm_scope,
	}

	# 处理多项目/多成员/多代码仓库过滤
	projects_filter = _parse_multi_values(project_id)
	members_filter = _parse_multi_values(member_id)
	repos_filter = _parse_multi_values(repository)

	target_project_names = []
	if projects_filter:
		for pid in projects_filter:
			if frappe.db.exists("Project", pid):
				target_project_names.append(frappe.db.get_value("Project", pid, "project_name") or pid)
			else:
				target_project_names.append(pid)
		filters["project"] = ["in", target_project_names]

	target_project_name = (
		target_project_names[0]
		if len(target_project_names) == 1
		else (", ".join(target_project_names) if target_project_names else None)
	)

	if members_filter:
		filters["member"] = ["in", members_filter]

	logs = frappe.get_all(
		"Daily Activity Log",
		filters=filters,
		fields=[
			"activity_date",
			"project",
			"member",
			"member_name",
			"commit_count",
			"total_lines",
			"file_count",
			"is_unclaimed",
			"raw_json",
		],
	)

	# 辅助函数：根据活动日期定位其所属时间槽位
	def find_slot_index(act_date_str):
		d = to_date_obj(act_date_str)
		for idx, (s_start, s_end) in enumerate(intervals):
			if s_start <= d <= s_end:
				return idx
		return None

	# 4. 统计与系列分组聚合
	project_series_data = defaultdict(lambda: [0] * num_slots)
	project_lines_data = defaultdict(lambda: [0] * num_slots)
	project_members_set = defaultdict(lambda: [set() for _ in range(num_slots)])
	series_meta = {}

	active_projects = set(frappe.get_all("Project", filters={"is_active": 1}, pluck="project_name"))
	total_period_commits = [0] * num_slots
	total_period_lines = [0] * num_slots

	for log in logs:
		# 排除已禁用的项目
		if log.project and log.project not in active_projects:
			continue

		commits_list = []
		if log.raw_json:
			try:
				parsed = json.loads(log.raw_json)
				if isinstance(parsed, list):
					commits_list = parsed
			except Exception:
				pass

		# 若指定了特定代码仓库过滤 (支持多仓库)
		if repos_filter:
			commits_list = [c for c in commits_list if c.get("repository") in repos_filter]
			if not commits_list:
				continue
			commits = len(commits_list)
			lines = sum(int(c.get("stats", {}).get("total") or 0) for c in commits_list)
		else:
			commits = int(log.commit_count or 0)
			lines = int(log.total_lines or 0)

		s_idx = find_slot_index(log.activity_date)
		if s_idx is None:
			continue

		p_name = log.project or "未分配项目"
		m_id = log.member or (log.member_name if log.is_unclaimed else "未知")

		total_period_commits[s_idx] += commits
		total_period_lines[s_idx] += lines

		# 如果指定了单个项目且未指定单个成员，按成员细分展示
		if len(target_project_names) == 1 and not member_id:
			series_key = log.member_name or m_id
			repos = project_repos_map.get(target_project_name, [])
			repo_str = ", ".join(repos) if repos else ""
			series_meta[series_key] = {
				"project_name": target_project_name,
				"repositories": repos,
				"repository_name": repo_str,
			}
		else:
			# 系列名称附加代码仓库名称，便于清晰区分
			repos = project_repos_map.get(p_name, [])
			if len(repos) == 1:
				repo_str = repos[0]
			elif len(repos) > 1:
				repo_str = f"{repos[0]} 等{len(repos)}个仓库"
			else:
				repo_str = ""

			if repo_str:
				series_key = f"{p_name} ({repo_str})"
			else:
				series_key = p_name

			series_meta[series_key] = {
				"project_name": p_name,
				"repositories": repos,
				"repository_name": ", ".join(repos) if repos else "",
			}

		project_series_data[series_key][s_idx] += commits
		project_lines_data[series_key][s_idx] += lines
		project_members_set[series_key][s_idx].add(m_id)

	series_list = []

	# 如果有汇总数据且有多个 series，添加一个总体对比线 (对比虚线规范)
	if len(project_series_data) > 1 and len(target_project_names) != 1:
		summary_title = "所选项目汇总" if target_project_names else "全部项目汇总"
		series_list.append(
			{
				"name": summary_title,
				"project_name": summary_title,
				"repositories": [],
				"repository_name": "",
				"commits": total_period_commits,
				"lines": total_period_lines,
				"is_total": True,
			}
		)

	for s_name, c_counts in sorted(
		project_series_data.items(),
		key=lambda x: sum(x[1]),
		reverse=True,
	):
		meta = series_meta.get(s_name, {})
		series_list.append(
			{
				"name": s_name,
				"project_name": meta.get("project_name", s_name),
				"repositories": meta.get("repositories", []),
				"repository_name": meta.get("repository_name", ""),
				"commits": c_counts,
				"lines": project_lines_data[s_name],
				"active_members": [len(m_set) for m_set in project_members_set[s_name]],
				"total_commits": sum(c_counts),
				"total_lines": sum(project_lines_data[s_name]),
				"is_total": False,
			}
		)

	# 如果没有任何提交记录，返回空占位 series
	if not series_list:
		display_name = target_project_name or "当前项目"
		meta = series_meta.get(display_name, {})
		series_list.append(
			{
				"name": display_name,
				"project_name": display_name,
				"repositories": meta.get("repositories", []),
				"repository_name": meta.get("repository_name", ""),
				"commits": [0] * num_slots,
				"lines": [0] * num_slots,
				"active_members": [0] * num_slots,
				"total_commits": 0,
				"total_lines": 0,
				"is_total": False,
			}
		)

	# 5. 趋势度量指标计算
	total_commits = sum(total_period_commits)
	total_lines_sum = sum(total_period_lines)
	avg_commits = round(total_commits / float(num_slots), 1) if num_slots else 0
	avg_lines = round(total_lines_sum / float(num_slots), 1) if num_slots else 0

	periods_dates = [s_start.strftime("%Y-%m-%d") for (s_start, s_end) in intervals]

	if interval == "day":
		benchmark_label = f"日均基准: {avg_commits}次/天"
		benchmark_lines_label = f"日均基准: {int(avg_lines):,}行/天"
		# 近 7 天 vs 前 7 天
		recent_commits = sum(total_period_commits[-7:])
		prev_commits = sum(total_period_commits[-14:-7]) if num_slots >= 14 else 0
	elif interval == "month":
		benchmark_label = f"月均基准: {avg_commits}次/月"
		benchmark_lines_label = f"月均基准: {int(avg_lines):,}行/月"
		# 近 2 个月 vs 前 2 个月
		recent_commits = sum(total_period_commits[-2:])
		prev_commits = sum(total_period_commits[-4:-2]) if num_slots >= 4 else 0
	else:
		benchmark_label = f"周均基准: {avg_commits}次/周"
		benchmark_lines_label = f"周均基准: {int(avg_lines):,}行/周"
		# 近 3 周 vs 前 3 周
		recent_commits = sum(total_period_commits[-3:])
		prev_commits = sum(total_period_commits[-6:-3]) if num_slots >= 6 else 0

	if prev_commits > 0:
		if recent_commits > prev_commits * 1.1:
			trend_direction = "up"
		elif recent_commits < prev_commits * 0.9:
			trend_direction = "down"
		else:
			trend_direction = "stable"
	else:
		trend_direction = "up" if recent_commits > 0 else "stable"

	return {
		"project_id": project_id,
		"project_name": target_project_name or "全部项目",
		"scope": norm_scope,
		"interval": interval,
		"member_id": member_id,
		"weeks": periods_short,  # 兼容 Frappe UI LineChart x 轴
		"periods": periods_short,
		"dates": periods_dates,
		"labels": periods_labels,
		"series": series_list,
		"summary": {
			"interval": interval,
			"total_commits": total_commits,
			"total_commits_12w": total_commits,  # 兼容原有字段名
			"total_lines": total_lines_sum,
			"average_commits": avg_commits,
			"average_weekly_commits": avg_commits,  # 兼容原有字段名
			"average_lines": avg_lines,
			"recent_commits": recent_commits,
			"recent_3w_commits": recent_commits,  # 兼容原有字段名
			"trend": trend_direction,
			"benchmark_label": benchmark_label,
			"benchmark_lines_label": benchmark_lines_label,
		},
		"repository": repository,
		"project_repos_map": dict(project_repos_map),
		"repositories": sorted(
			list({r.name for r in frappe.get_all("Codeup Repository", fields=["name"]) if r.name})
		),
	}


def get_12_week_trend(
	project_id: str = "all",
	scope: str = "all",
	member_id: str | None = None,
	ref_date: str | None = None,
	interval: str = "week",
	days: int = 30,
) -> dict:
	"""
	兼容旧版接口调用，默认拉取 12 周按周汇总
	"""
	return get_activity_trend(
		project_id=project_id,
		scope=scope,
		member_id=member_id,
		ref_date=ref_date,
		interval=interval,
		days=days,
	)
