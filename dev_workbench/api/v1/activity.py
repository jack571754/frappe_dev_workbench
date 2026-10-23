# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from dev_workbench.permissions import require_manager as verify_manager_permission


def _parse_multi_values(val):
	"""
	将多种参数输入格式规范化为非空字符串列表：
	- None / '' / 'all' -> []
	- 'p1,p2,p3' -> ['p1', 'p2', 'p3']
	- '["p1", "p2"]' -> ['p1', 'p2']
	- ['p1', 'p2'] -> ['p1', 'p2']
	"""
	if not val:
		return []
	if isinstance(val, (list, tuple, set)):
		return [str(x).strip() for x in val if str(x).strip() and str(x).strip() != "all"]
	if isinstance(val, str):
		val = val.strip()
		if not val or val == "all":
			return []
		if val.startswith("[") and val.endswith("]"):
			try:
				parsed = json.loads(val)
				if isinstance(parsed, list):
					return [str(x).strip() for x in parsed if str(x).strip() and str(x).strip() != "all"]
			except Exception:
				pass
		return [x.strip() for x in val.split(",") if x.strip() and x.strip() != "all"]
	return []


@frappe.whitelist(methods=["GET"])
def get_daily_activity(member_id=None, date=None, scope="all", branch=None):
	"""
	获取指定成员在指定日期的处理后提交活动数据
	:param member_id: 成员 ID (例如 MEM-6311) 或 'unclaimed' (未归属)
	:param date: 目标日期 (YYYY-MM-DD)
	:param scope: 分支统计范围 ('all' 或 'default')
	:param branch: 特定分支名筛选
	"""
	verify_manager_permission()

	if not member_id or not date:
		frappe.throw(_("缺少必需参数: member_id 或 date"))

	scope = (scope or "all").lower()
	is_unclaimed = 1 if member_id in ("unclaimed", "unassigned", "未归属") else 0

	filters = {
		"activity_date": date,
		"branch_scope": scope,
	}

	if is_unclaimed:
		filters["is_unclaimed"] = 1
	else:
		# 支持通过邮箱查找对应成员 ID
		actual_member_id = member_id
		if "@" in member_id:
			found_mem = frappe.db.get_value("Project Member", {"email": member_id}, "name")
			if found_mem:
				actual_member_id = found_mem
		filters["member"] = actual_member_id

	logs = frappe.get_all(
		"Daily Activity Log",
		filters=filters,
		fields=[
			"name",
			"member",
			"member_name",
			"activity_date",
			"project",
			"commit_count",
			"lines_added",
			"lines_deleted",
			"total_lines",
			"file_count",
			"branch_scope",
			"is_unclaimed",
			"lines_unknown",
			"summary",
			"raw_json",
		],
	)

	if not logs:
		# 无活动记录
		member_name = (
			"未归属提交"
			if is_unclaimed
			else (frappe.db.get_value("Project Member", member_id, "member_name") or member_id)
		)
		return {
			"member_id": member_id,
			"member_name": member_name,
			"date": date,
			"scope": scope,
			"branch": branch or "all",
			"commit_count": 0,
			"lines_added": 0,
			"lines_deleted": 0,
			"total_lines": 0,
			"file_count": 0,
			"lines_unknown": 0,
			"summary": None,
			"projects": [],
			"commits": [],
		}

	# 聚合可能属于多个项目的日志
	total_commits = 0
	total_adds = 0
	total_dels = 0
	total_lines = 0
	total_files = 0
	lines_unknown = 0
	summaries = []
	projects = set()
	all_commits = []
	member_name = logs[0].member_name

	for l in logs:
		if l.lines_unknown:
			lines_unknown = 1
		if l.summary:
			summaries.append(l.summary)
		if l.project:
			projects.add(l.project)

		if l.raw_json:
			try:
				parsed_commits = json.loads(l.raw_json)
				if isinstance(parsed_commits, list):
					all_commits.extend(parsed_commits)
			except Exception:
				pass

	# 支持按分支名过滤 (支持单分支或多分支)
	branches_filter = _parse_multi_values(branch)
	if branches_filter:
		all_commits = [
			c
			for c in all_commits
			if (c.get("branch") and c.get("branch") in branches_filter)
			or (c.get("branches") and any(b in branches_filter for b in c.get("branches")))
		]

	total_commits = len(all_commits)
	total_adds = sum(int(c.get("stats", {}).get("additions") or 0) for c in all_commits)
	total_dels = sum(int(c.get("stats", {}).get("deletions") or 0) for c in all_commits)
	total_lines = total_adds + total_dels
	total_files = len(set(f.get("path") for c in all_commits for f in (c.get("files") or []))) or (
		1 if all_commits else 0
	)

	return {
		"member_id": member_id,
		"member_name": member_name,
		"date": date,
		"scope": scope,
		"branch": branch or "all",
		"commit_count": total_commits,
		"lines_added": total_adds,
		"lines_deleted": total_dels,
		"total_lines": total_lines,
		"file_count": total_files,
		"lines_unknown": lines_unknown,
		"summary": "\n".join(summaries) if summaries else None,
		"projects": list(projects),
		"commits": all_commits,
	}


@frappe.whitelist(methods=["POST"])
def regenerate_summary(log_name=None, member_id=None, date=None, scope="all"):
	"""
	强制重新为指定活动日志生成 AI 摘要。
	"""
	verify_manager_permission()
	from dev_workbench.services.ai_summary_service import generate_summary_for_activity_log

	if not log_name:
		if not member_id or not date:
			frappe.throw(_("请提供 log_name 或 (member_id, date)"))
		filters = {
			"activity_date": date,
			"branch_scope": (scope or "all").lower(),
		}
		if member_id in ("unclaimed", "unassigned", "未归属"):
			filters["is_unclaimed"] = 1
		else:
			filters["member"] = member_id
		log_name = frappe.db.get_value("Daily Activity Log", filters, "name")
		if not log_name:
			frappe.throw(_("未找到匹配的活动日志记录"))

	summary = generate_summary_for_activity_log(log_name, force=True)
	return {
		"status": "success",
		"log_name": log_name,
		"summary": summary,
	}


@frappe.whitelist(methods=["POST"])
def trigger_batch_summaries(date=None, is_async=1, force=0):
	"""
	批量触发指定日期的 AI 摘要生成
	"""
	verify_manager_permission()
	from dev_workbench.services.ai_summary_service import (
		enqueue_summary_generation,
		generate_daily_summaries_for_date,
	)

	is_async = int(is_async or 1)
	force = bool(int(force or 0))

	if is_async:
		res = enqueue_summary_generation(date=date, force=force)
		return {"status": "enqueued", "data": res}
	else:
		res = generate_daily_summaries_for_date(date=date, force=force)
		return {"status": "completed", "data": res}


@frappe.whitelist(methods=["GET"])
def get_daily_overview(
	date=None,
	start_date=None,
	end_date=None,
	scope="all",
	project=None,
	repository=None,
	branch=None,
	member=None,
	member_id=None,
):
	"""
	获取指定日期或时间段内所有成员的提交活动总览与明细
	用于主看板【成员日报】视图，支持项目、具体代码仓库、分支及成员筛选 (均支持多选)
	"""
	verify_manager_permission()
	scope = (scope or "all").lower()

	projects_filter = _parse_multi_values(project)
	repos_filter = _parse_multi_values(repository)
	branches_filter = _parse_multi_values(branch)
	members_filter = _parse_multi_values(member or member_id)

	if not date and not start_date:
		from dev_workbench.services.feishu_report_service import get_default_report_date

		date = get_default_report_date()

	filters = {"branch_scope": scope}
	if start_date and end_date:
		filters["activity_date"] = ["between", [start_date, end_date]]
	else:
		filters["activity_date"] = date

	# 获取当前已启用的项目清单 (禁用项目不展示)
	active_projects_list = frappe.get_all(
		"Project",
		filters={"is_active": 1},
		fields=["name", "project_name"],
	)
	all_projects = sorted(list(set(p.project_name or p.name for p in active_projects_list)))
	active_project_names = set(all_projects)
	active_project_ids = set(p.name for p in active_projects_list)

	# 获取当前已启用的代码仓库清单 (禁用仓库不展示)
	all_repos = frappe.get_all(
		"Codeup Repository",
		filters={"is_active": 1},
		fields=["name", "repository_name", "default_branch"],
		order_by="repository_name asc",
	)
	active_repo_names = set(r["repository_name"] for r in all_repos if r.get("repository_name"))
	active_repo_names.update(r["name"] for r in all_repos if r.get("name"))

	# 查询项目与代码仓库的关联映射 (仅关联启用的项目与启用的代码仓库)
	repo_items = frappe.get_all("Project Repository Item", fields=["parent", "repository"])
	project_repos_map = {}
	for it in repo_items:
		is_proj_active = it.parent in active_project_names or it.parent in active_project_ids
		is_repo_active = it.repository in active_repo_names
		if is_proj_active and is_repo_active:
			if it.parent not in project_repos_map:
				project_repos_map[it.parent] = []
			if it.repository not in project_repos_map[it.parent]:
				project_repos_map[it.parent].append(it.repository)

	# 建立项目 ID 与名称双向映射，支持用户以 ID 或名称筛选
	project_name_map = {}
	for p in active_projects_list:
		project_name_map[p.name] = p.project_name or p.name
		if p.project_name:
			project_name_map[p.project_name] = p.project_name

	normalized_projects_filter = set()
	for p in projects_filter:
		mapped = project_name_map.get(p) or p
		normalized_projects_filter.add(mapped)

	# 仅获取当前已启用的成员清单 (禁用成员不展示)
	active_members = frappe.get_all(
		"Project Member",
		filters={"is_active": 1},
		fields=["name", "member_name", "department", "email", "is_manager"],
	)
	member_map = {m.name: m for m in active_members}
	member_by_name = {m.member_name: m for m in active_members if m.member_name}
	member_by_email = {m.email: m for m in active_members if m.email}

	# 规范化成员筛选条件（支持 ID、姓名、邮箱）
	normalized_members_filter = set()
	include_unclaimed = False
	for mf in members_filter:
		if mf in ("unclaimed", "未归属", "未归属提交"):
			include_unclaimed = True
		else:
			normalized_members_filter.add(mf)
			if mf in member_map:
				normalized_members_filter.add(member_map[mf].member_name)
			elif mf in member_by_name:
				normalized_members_filter.add(member_by_name[mf].name)
			elif mf in member_by_email:
				normalized_members_filter.add(member_by_email[mf].name)

	# 读取活动记录日志（不在 SQL 阶段强过滤 project，以便能按仓库关联推导与保留未归属提交）
	logs = frappe.get_all(
		"Daily Activity Log",
		filters=filters,
		fields=[
			"name",
			"member",
			"member_name",
			"activity_date",
			"project",
			"commit_count",
			"lines_added",
			"lines_deleted",
			"total_lines",
			"file_count",
			"lines_unknown",
			"is_unclaimed",
			"summary",
			"raw_json",
		],
		order_by="commit_count desc",
	)

	member_activity_map = {}
	available_branches = set()
	unclaimed_data = {
		"member_id": "unclaimed",
		"member_name": "未归属提交",
		"commit_count": 0,
		"lines_added": 0,
		"lines_deleted": 0,
		"total_lines": 0,
		"file_count": 0,
		"lines_unknown": 0,
		"projects": set(),
		"repositories": set(),
		"summaries": [],
		"commits": [],
	}

	for l in logs:
		# 1. 严格排除已被禁用的项目
		if l.project and l.project not in active_project_names:
			continue

		# 2. 严格排除已被禁用的成员（未归属提交除外）
		if not l.is_unclaimed:
			m_id = l.member
			if not m_id or m_id not in member_map:
				continue

		# 3. 成员筛选过滤
		if members_filter:
			if l.is_unclaimed:
				if not include_unclaimed:
					continue
			else:
				m_id = l.member
				m_name = l.member_name
				matched = m_id in normalized_members_filter or m_name in normalized_members_filter
				if not matched:
					continue

		# 4. 解析提交记录，并严格排除已禁用仓库的提交
		parsed_commits = []
		if l.raw_json:
			try:
				c_parsed = json.loads(l.raw_json)
				if isinstance(c_parsed, list):
					for c in c_parsed:
						repo = c.get("repository")
						# 仅保留属于启用状态仓库的提交，排除已禁用的仓库
						if not repo or repo in active_repo_names:
							parsed_commits.append(c)
							if c.get("branch"):
								available_branches.add(c["branch"])
							if c.get("branches") and isinstance(c["branches"], list):
								available_branches.update(c["branches"])
			except Exception:
				pass

		# 提取有效启用的代码仓库
		log_repos = set()
		for c in parsed_commits:
			r = c.get("repository")
			if r and r in active_repo_names:
				log_repos.add(r)
		if not log_repos and l.project in project_repos_map:
			log_repos.update(project_repos_map[l.project])

		# 若该日志所有提交均属于已禁用仓库且无有效启用仓库，则直接跳过
		if l.raw_json and not parsed_commits and not log_repos:
			continue

		# 项目筛选匹配逻辑：
		# 若指定了项目筛选，匹配条件为：日志的 project 匹配，或者其提交涉及的代码仓库属于该项目
		if normalized_projects_filter:
			log_project = l.project
			proj_matched = log_project in normalized_projects_filter
			if not proj_matched:
				for p in normalized_projects_filter:
					allowed_repos = project_repos_map.get(p, [])
					if any(r in allowed_repos for r in log_repos):
						proj_matched = True
						break
			if not proj_matched:
				continue

		# 代码仓库筛选 (多选匹配，支持大小写不敏感)
		if repos_filter:
			norm_rf = set(r.lower() for r in repos_filter)
			parsed_commits = [
				c for c in parsed_commits if c.get("repository") and c.get("repository").lower() in norm_rf
			]
			if not parsed_commits:
				# 若为纯元数据记录无 raw_json，但 log_repos 匹配
				if not any(r.lower() in norm_rf for r in log_repos):
					continue

		# 代码分支筛选 (多选匹配)
		if branches_filter:
			norm_bf = set(b.lower() for b in branches_filter)
			parsed_commits = [
				c
				for c in parsed_commits
				if (c.get("branch") and str(c.get("branch")).lower() in norm_bf)
				or (c.get("branches") and any(str(b).lower() in norm_bf for b in c.get("branches")))
			]
			if not parsed_commits and l.raw_json:
				continue

		if repos_filter or branches_filter:
			if parsed_commits:
				c_count = len(parsed_commits)
				l_adds = sum(int(c.get("stats", {}).get("additions") or 0) for c in parsed_commits)
				l_dels = sum(int(c.get("stats", {}).get("deletions") or 0) for c in parsed_commits)
				l_total = sum(int(c.get("stats", {}).get("total") or 0) for c in parsed_commits)
				f_count = len(set(f.get("path") for c in parsed_commits for f in (c.get("files") or []))) or 1
			else:
				c_count = int(l.commit_count or 0)
				l_adds = int(l.lines_added or 0)
				l_dels = int(l.lines_deleted or 0)
				l_total = int(l.total_lines or 0)
				f_count = int(l.file_count or 0)
		else:
			c_count = int(l.commit_count or 0)
			l_adds = int(l.lines_added or 0)
			l_dels = int(l.lines_deleted or 0)
			l_total = int(l.total_lines or 0)
			f_count = int(l.file_count or 0)

		# 刷新实际涉及的仓库
		current_repos = set()
		for c in parsed_commits:
			r = c.get("repository")
			if r:
				current_repos.add(r)
		if not current_repos:
			current_repos = log_repos

		if l.is_unclaimed:
			unclaimed_data["commit_count"] += c_count
			unclaimed_data["lines_added"] += l_adds
			unclaimed_data["lines_deleted"] += l_dels
			unclaimed_data["total_lines"] += l_total
			unclaimed_data["file_count"] += f_count
			if l.lines_unknown:
				unclaimed_data["lines_unknown"] = 1
			if l.project:
				unclaimed_data["projects"].add(l.project)
			unclaimed_data["repositories"].update(current_repos)
			if l.summary:
				unclaimed_data["summaries"].append(l.summary)
			unclaimed_data["commits"].extend(parsed_commits)
			continue

		m_id = l.member
		if not m_id:
			continue

		if m_id not in member_activity_map:
			m_info = member_map.get(m_id)
			member_activity_map[m_id] = {
				"member_id": m_id,
				"member_name": l.member_name or (m_info.member_name if m_info else m_id),
				"department": m_info.department if m_info else "",
				"email": m_info.email if m_info else "",
				"is_manager": m_info.is_manager if m_info else 0,
				"commit_count": 0,
				"lines_added": 0,
				"lines_deleted": 0,
				"total_lines": 0,
				"file_count": 0,
				"lines_unknown": 0,
				"projects": set(),
				"repositories": set(),
				"summaries": [],
				"commits": [],
				"has_commits": True,
			}

		m_entry = member_activity_map[m_id]
		m_entry["commit_count"] += c_count
		m_entry["lines_added"] += l_adds
		m_entry["lines_deleted"] += l_dels
		m_entry["total_lines"] += l_total
		m_entry["file_count"] += f_count
		if l.lines_unknown:
			m_entry["lines_unknown"] = 1
		if l.project:
			m_entry["projects"].add(l.project)
		m_entry["repositories"].update(current_repos)
		if l.summary:
			m_entry["summaries"].append(l.summary)
		m_entry["commits"].extend(parsed_commits)

	members_list = []
	for entry in member_activity_map.values():
		entry["projects"] = sorted(list(entry["projects"]))
		entry["repositories"] = sorted(list(entry["repositories"]))
		entry["summary"] = "\n".join(entry["summaries"]) if entry["summaries"] else "常规代码提交与维护"
		members_list.append(entry)

	members_list.sort(key=lambda x: x["commit_count"], reverse=True)

	unclaimed_data["projects"] = sorted(list(unclaimed_data["projects"]))
	unclaimed_data["repositories"] = sorted(list(unclaimed_data["repositories"]))
	unclaimed_data["summary"] = (
		"\n".join(unclaimed_data["summaries"]) if unclaimed_data["summaries"] else "未归属开发者提交"
	)
	unclaimed_data["has_commits"] = unclaimed_data["commit_count"] > 0

	total_active_members = len(members_list)
	total_commits = sum(m["commit_count"] for m in members_list)
	total_lines = sum(m["total_lines"] for m in members_list)

	target_check_date = date or end_date or frappe.utils.nowdate()
	absent_count = frappe.db.count("Absence Record", {"check_date": target_check_date, "status": "待跟进"})

	# 汇总可用的所有项目与仓库选项
	project_options = [
		{
			"name": p,
			"repo_display": ", ".join(project_repos_map.get(p, [])),
			"repositories": project_repos_map.get(p, []),
		}
		for p in all_projects
	]

	for r in all_repos:
		if r.get("default_branch"):
			available_branches.add(r["default_branch"])

	if not available_branches:
		available_branches.add("master")

	# 返回全体活跃成员主清单，确保前端下拉选项不会因局部筛选而丢失或产生孤儿值
	all_members_master = [
		{
			"member_id": m.name,
			"member_name": m.member_name or m.name,
			"department": m.department or "",
			"email": m.email or "",
		}
		for m in active_members
	]

	return {
		"date": date,
		"start_date": start_date,
		"end_date": end_date,
		"scope": scope,
		"branch": branch or "all",
		"selected_branch": branch or "all",
		"selected_branches": branches_filter,
		"selected_projects": projects_filter,
		"selected_repositories": repos_filter,
		"selected_members": members_filter,
		"branches": sorted(list(available_branches)),
		"available_branches": sorted(list(available_branches)),
		"metrics": {
			"active_members_count": total_active_members,
			"total_commits": total_commits,
			"total_lines": total_lines,
			"unclaimed_commits": unclaimed_data["commit_count"],
			"absent_count": absent_count,
		},
		"projects": all_projects,
		"project_options": project_options,
		"project_repos_map": project_repos_map,
		"repositories": [r["repository_name"] or r["name"] for r in all_repos],
		"repository_records": all_repos,
		"all_members": all_members_master,
		"members": members_list,
		"unclaimed": unclaimed_data if unclaimed_data["has_commits"] else None,
	}


@frappe.whitelist(methods=["GET"])
def get_project_trend(
	project_id="all", scope="all", member_id=None, ref_date=None, interval="week", days=30, repository=None
):
	"""
	获取项目研发活跃度趋势数据 (支持按天、按周、按月聚合及代码仓库筛选)
	返回指定项目的活跃度趋势。
	"""
	verify_manager_permission()
	from dev_workbench.services.trend_service import get_activity_trend

	return get_activity_trend(
		project_id=project_id,
		scope=scope,
		member_id=member_id,
		ref_date=ref_date,
		interval=interval,
		days=days,
		repository=repository or frappe.form_dict.get("repository"),
	)
