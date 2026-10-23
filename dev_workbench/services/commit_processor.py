# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import fnmatch
import json
import re
from datetime import UTC, datetime, timedelta, timezone

import frappe
from frappe import _

BEIJING_TZ = timezone(timedelta(hours=8))

# 内置默认排除文件规则 (glob)
DEFAULT_EXCLUDE_RULES = [
	"*.lock",
	"package-lock.json",
	"yarn.lock",
	"pnpm-lock.yaml",
	"dist/**",
	"build/**",
	"public/**",
	"*.min.js",
	"*.min.css",
	"node_modules/**",
]


def matches_exclude_rule(filepath: str, rules: list[str]) -> bool:
	"""
	检查文件路径是否匹配排除规则 (Glob)
	:param filepath: 相对文件路径
	:param rules: glob 模式列表
	"""
	if not filepath or not rules:
		return False

	clean_path = filepath.replace("\\", "/").strip().lstrip("/")
	filename = clean_path.split("/")[-1]

	for rule in rules:
		if not rule:
			continue
		pattern = rule.strip().replace("\\", "/").lstrip("/")
		if not pattern or pattern.startswith("#"):
			continue

		# 精确匹配
		if clean_path == pattern:
			return True

		# 后缀匹配，例如 *.lock 或 *.min.js
		if pattern.startswith("*."):
			suffix = pattern[1:]
			if clean_path.endswith(suffix) or filename.endswith(suffix):
				return True

		# 目录通配符，例如 dist/** 或 node_modules/**
		if pattern.endswith("/**"):
			prefix = pattern[:-3]
			if (
				clean_path == prefix
				or clean_path.startswith(prefix + "/")
				or f"/{prefix}/" in f"/{clean_path}"
			):
				return True

		# 简单目录通配，例如 dist/*
		if pattern.endswith("/*"):
			prefix = pattern[:-2]
			if clean_path.startswith(prefix + "/"):
				return True

		# 标准 fnmatch
		if fnmatch.fnmatch(clean_path, pattern) or fnmatch.fnmatch(filename, pattern):
			return True

	return False


def is_merge_commit(commit: dict) -> bool:
	"""
	根据 parentIds 长度判断是否为 merge commit (长度 > 1 为 merge)
	"""
	parents = commit.get("parentIds") or commit.get("parents") or []
	if len(parents) > 1:
		return True

	# 辅助判断：提交信息包含标准 Merge 分支格式
	title = commit.get("title") or (commit.get("message") or "").split("\n")[0]
	if (
		title.startswith("Merge branch ")
		or title.startswith("Merge pull request ")
		or title.startswith("Merge remote-tracking branch ")
	):
		return True

	return False


def parse_author_date_beijing(authored_date) -> tuple[str, str]:
	"""
	解析 commit 的 author date 为北京时间 (UTC+8)
	返回 (date_str: 'YYYY-MM-DD', datetime_str: 'YYYY-MM-DD HH:MM:SS')
	"""
	if not authored_date:
		now_bj = datetime.now(BEIJING_TZ)
		return now_bj.strftime("%Y-%m-%d"), now_bj.strftime("%Y-%m-%d %H:%M:%S")

	if isinstance(authored_date, datetime):
		dt = authored_date
		if dt.tzinfo is None:
			# 假设无时区为 UTC
			dt = dt.replace(tzinfo=UTC)
		dt_bj = dt.astimezone(BEIJING_TZ)
		return dt_bj.strftime("%Y-%m-%d"), dt_bj.strftime("%Y-%m-%d %H:%M:%S")

	# 字符串解析
	raw = str(authored_date).strip()
	try:
		# 处理 ISO 8601 (带 Z 或时区偏移)
		clean_iso = raw.replace("Z", "+00:00")
		dt = datetime.fromisoformat(clean_iso)
		if dt.tzinfo is None:
			dt = dt.replace(tzinfo=UTC)
		dt_bj = dt.astimezone(BEIJING_TZ)
		return dt_bj.strftime("%Y-%m-%d"), dt_bj.strftime("%Y-%m-%d %H:%M:%S")
	except Exception:
		# 尝试常用格式解析
		for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
			try:
				dt = datetime.strptime(raw[:19], fmt)
				dt_bj = dt.replace(tzinfo=BEIJING_TZ)
				return dt_bj.strftime("%Y-%m-%d"), dt_bj.strftime("%Y-%m-%d %H:%M:%S")
			except Exception:
				continue

	# 降级使用当前北京时间
	now_bj = datetime.now(BEIJING_TZ)
	return now_bj.strftime("%Y-%m-%d"), now_bj.strftime("%Y-%m-%d %H:%M:%S")


class CommitProcessor:
	"""
	提交数据处理核心引擎：
	- Commit hash 去重（同一 hash 在多分支上只计一次）
	- Merge commit 过滤（排除 parentIds > 1 的提交）
	- 排除文件规则匹配（过滤排除文件行数，保留文件列表展示）
	- 成员映射（commit.author.email -> Git Identity -> Project Member）
	- 行数未知状态标记
	- 每日聚合生成 DailyActivityLog 记录（包含未归属提交单独记录）
	"""

	def __init__(self, branch_scope="all"):
		self.branch_scope = branch_scope
		self.seen_commit_shas = set()
		self.commits_by_id = {}
		# 聚合桶：key 为 (member_id, date_str, project_name, branch_scope)
		self.aggregated_data = {}
		self.unclaimed_commits = []

	def map_author(self, author_email: str, author_name: str | None = None) -> tuple[str, str, int]:
		"""
		按 author.email 匹配 GitIdentity -> ProjectMember
		返回 (member_id, member_name, is_unclaimed: 0/1)
		"""
		clean_email = (author_email or "").strip().lower()
		if not clean_email:
			return None, author_name or "未知开发者", 1

		# 查询 Git Identity 表
		git_identities = frappe.get_all(
			"Git Identity",
			filters={"identity": clean_email},
			fields=["name", "member", "status"],
			limit=1,
		)

		if git_identities and git_identities[0].member:
			member_id = git_identities[0].member
			member_name = frappe.db.get_value("Project Member", member_id, "member_name") or member_id
			return member_id, member_name, 0

		# 若不存在则自动登记未认领 Git 身份
		if not git_identities:
			try:
				new_git_id = frappe.new_doc("Git Identity")
				new_git_id.identity = clean_email
				new_git_id.identity_type = "Email"
				new_git_id.status = "待认领"
				new_git_id.flags.ignore_permissions = True
				new_git_id.insert()
			except Exception:
				pass

		return None, author_name or clean_email.split("@")[0], 1

	def process_commit(
		self,
		commit: dict,
		project_name: str,
		repo_name: str,
		custom_exclude_rules: list | None = None,
		branch_name: str | None = None,
	):
		"""
		处理单条提交记录：去重、过滤 merge commit、排除文件计算、身份映射与聚合
		"""
		commit_id = commit.get("id") or commit.get("sha") or commit.get("shortId")
		if not commit_id:
			return None

		branch = branch_name or commit.get("branch") or "master"

		# 1. Commit Hash 去重
		if commit_id in self.seen_commit_shas:
			# 同一 hash 在多分支上出现，不重复计入行数/提交数，但将其所属分支追加至 branches 属性中
			if hasattr(self, "commits_by_id") and commit_id in self.commits_by_id:
				existing_c = self.commits_by_id[commit_id]
				if "branches" not in existing_c:
					existing_c["branches"] = [existing_c.get("branch")] if existing_c.get("branch") else []
				if branch and branch not in existing_c["branches"]:
					existing_c["branches"].append(branch)
			return None
		self.seen_commit_shas.add(commit_id)

		# 2. Merge commit 排除
		if is_merge_commit(commit):
			return None

		# 3. 解析时间（北京时间 UTC+8）
		authored_date = commit.get("authoredDate") or commit.get("authored_date")
		date_str, datetime_bj = parse_author_date_beijing(authored_date)

		# 4. 成员映射
		author_email = commit.get("authorEmail") or (commit.get("author") or {}).get("email")
		author_name = commit.get("authorName") or (commit.get("author") or {}).get("name")
		member_id, member_name, is_unclaimed = self.map_author(author_email, author_name)

		# 5. 代码行数与排除文件处理
		all_rules = list(DEFAULT_EXCLUDE_RULES)
		if custom_exclude_rules:
			all_rules.extend(custom_exclude_rules)

		stats = commit.get("stats")
		files = commit.get("files") or []

		lines_unknown = False
		additions = 0
		deletions = 0
		file_count = len(files) if files else 1

		# 若包含文件变更明细，应用排除文件规则
		if files:
			valid_files = 0
			file_adds = 0
			file_dels = 0
			for f in files:
				f_path = f.get("path") or f.get("filename") or ""
				f_add = int(f.get("additions") or 0)
				f_del = int(f.get("deletions") or 0)

				# 排除文件规则判断
				if not matches_exclude_rule(f_path, all_rules):
					file_adds += f_add
					file_dels += f_del
					valid_files += 1

			additions = file_adds
			deletions = file_dels
			file_count = max(len(files), 1)
		elif stats and isinstance(stats, dict) and stats.get("total") is not None:
			additions = int(stats.get("additions") or 0)
			deletions = int(stats.get("deletions") or 0)
		else:
			# 行数未知标记
			lines_unknown = True
			additions = 0
			deletions = 0

		total_lines = additions + deletions

		# 6. 打包结构化提交记录供 JSON 审计
		clean_commit_data = {
			"id": commit_id,
			"short_id": commit.get("shortId") or commit_id[:8],
			"title": commit.get("title") or (commit.get("message") or "").split("\n")[0],
			"message": commit.get("message") or commit.get("title") or "",
			"author_name": author_name,
			"author_email": author_email,
			"authored_date": datetime_bj,
			"date": date_str,
			"project": project_name,
			"repository": repo_name,
			"branch": branch,
			"branches": [branch] if branch else [],
			"stats": {
				"additions": additions,
				"deletions": deletions,
				"total": total_lines,
				"unknown": lines_unknown,
			},
			"files_count": file_count,
			"files": files,
		}
		if hasattr(self, "commits_by_id"):
			self.commits_by_id[commit_id] = clean_commit_data

		# 7. 写入聚合桶
		bucket_key = (
			member_id or f"unclaimed:{author_email or author_name}",
			date_str,
			project_name or "未分配项目",
			self.branch_scope,
		)

		if bucket_key not in self.aggregated_data:
			self.aggregated_data[bucket_key] = {
				"member": member_id,
				"member_name": member_name,
				"activity_date": date_str,
				"project": project_name,
				"branch_scope": self.branch_scope,
				"is_unclaimed": is_unclaimed,
				"commit_count": 0,
				"lines_added": 0,
				"lines_deleted": 0,
				"total_lines": 0,
				"file_count": 0,
				"lines_unknown": 0,
				"commits": [],
			}

		bucket = self.aggregated_data[bucket_key]
		bucket["commit_count"] += 1
		bucket["lines_added"] += additions
		bucket["lines_deleted"] += deletions
		bucket["total_lines"] += total_lines
		bucket["file_count"] += file_count
		if lines_unknown:
			bucket["lines_unknown"] = 1
		bucket["commits"].append(clean_commit_data)

		if is_unclaimed:
			self.unclaimed_commits.append(clean_commit_data)

		return clean_commit_data

	def save_to_database(
		self, auto_generate_summary: bool = False, auto_enqueue_summary: bool = False
	) -> list[str]:
		"""
		将聚合数据持久化至 DailyActivityLog 数据库表
		若同成员、同日期、同项目、同分支范围的记录已存在则合并更新
		:param auto_generate_summary: 是否同步生成 AI 摘要
		:param auto_enqueue_summary: 是否推入后台队列异步生成 AI 摘要
		"""
		saved_log_names = []
		dates_to_enqueue = set()

		for item in self.aggregated_data.values():
			member_id = item["member"]
			activity_date = item["activity_date"]
			project = item["project"]
			branch_scope = item["branch_scope"]
			is_unclaimed = item["is_unclaimed"]

			# 查询已存在的 DailyActivityLog
			filters = {
				"activity_date": activity_date,
				"branch_scope": branch_scope,
			}
			if member_id:
				filters["member"] = member_id
			else:
				filters["is_unclaimed"] = 1
				filters["member_name"] = item["member_name"]

			if project and frappe.db.exists("Project", project):
				filters["project"] = project

			existing_logs = frappe.get_all(
				"Daily Activity Log",
				filters=filters,
				fields=["name"],
				limit=1,
			)

			if existing_logs:
				log_doc = frappe.get_doc("Daily Activity Log", existing_logs[0].name)
			else:
				log_doc = frappe.new_doc("Daily Activity Log")
				log_doc.activity_date = activity_date
				log_doc.branch_scope = branch_scope
				log_doc.is_unclaimed = is_unclaimed
				if member_id:
					log_doc.member = member_id
				if project and frappe.db.exists("Project", project):
					log_doc.project = project

			log_doc.member_name = item["member_name"]
			log_doc.commit_count = item["commit_count"]
			log_doc.lines_added = item["lines_added"]
			log_doc.lines_deleted = item["lines_deleted"]
			log_doc.total_lines = item["total_lines"]
			log_doc.file_count = item["file_count"]
			log_doc.lines_unknown = item["lines_unknown"]
			log_doc.raw_json = json.dumps(item["commits"], ensure_ascii=False, indent=2)

			log_doc.flags.ignore_permissions = True
			log_doc.save()
			saved_log_names.append(log_doc.name)
			dates_to_enqueue.add(activity_date)

			if auto_generate_summary:
				try:
					from dev_workbench.services.ai_summary_service import generate_summary_for_activity_log

					generate_summary_for_activity_log(log_doc.name)
				except Exception as e:
					frappe.log_error(title=f"同步生成 AI 摘要失败 [{log_doc.name}]", message=str(e))

		frappe.db.commit()

		if auto_enqueue_summary and dates_to_enqueue:
			try:
				from dev_workbench.services.ai_summary_service import enqueue_summary_generation

				for d in dates_to_enqueue:
					enqueue_summary_generation(date=d)
			except Exception as e:
				frappe.log_error(title="推入 AI 摘要后台任务失败", message=str(e))

		return saved_log_names
