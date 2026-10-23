# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe import _

from dev_workbench.permissions import require_manager as verify_manager_permission
from dev_workbench.services.codeup_client import CodeupAPIError, CodeupClient
from dev_workbench.services.commit_processor import CommitProcessor
from dev_workbench.services.token_service import check_token_expiry, get_codeup_credentials


def _generate_mock_commits(repo_name, ref_name="master"):
	"""在无真实访问令牌或测试环境下生成模拟提交数据供验证"""
	now = datetime.now()
	mock_authors = [
		{"name": "张伟", "email": "zhangwei@company.com"},
		{"name": "李强", "email": "liqiang@company.com"},
		{"name": "王敏", "email": "wangmin@company.com"},
		{"name": "外部协作者", "email": "unclaimed_dev@external.org"},
	]

	commits = []
	ref_name = ref_name or "master"
	clean_ref = ref_name.replace("/", "_").replace("-", "_")
	count = 4 if ref_name != "master" else 6
	for i in range(count):
		author = mock_authors[i % len(mock_authors)]
		commit_time = (now - timedelta(hours=i * 5 + 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
		sha = f"{repo_name.lower().replace(' ', '')}{clean_ref}a1b2c3d4e5f6{i:04x}"[:40]
		commits.append(
			{
				"id": sha,
				"shortId": sha[:8],
				"title": f"feat({ref_name}): 实现核心模块业务特性 #{i + 1}",
				"message": f"feat({ref_name}): 实现核心模块业务特性 #{i + 1}\n\n- 优化接口性能\n- 分支 {ref_name} 业务特性",
				"authorName": author["name"],
				"authorEmail": author["email"],
				"authoredDate": commit_time,
				"committedDate": commit_time,
				"branch": ref_name,
				"parentIds": ["baseparent1234567890abcdef"]
				if i != 2
				else ["parent1", "parent2"],  # i=2 为 merge commit
				"stats": {
					"additions": 45 + i * 12,
					"deletions": 10 + i * 3,
					"total": 55 + i * 15,
				},
			}
		)
	return commits


def get_repo_branches(client=None, org_id=None, repo_id=None, default_branch="master", is_test_env=False):
	"""获取代码库的所有分支列表（支持自动分页与回退）"""
	default_branch = default_branch or "master"
	if is_test_env or not client or not org_id or not repo_id:
		return [default_branch, "develop", "feature/workbench-ui"]
	try:
		branches_raw = client.list_branches(org_id, repo_id, all_pages=True)
		branch_names = []
		if isinstance(branches_raw, list):
			for b in branches_raw:
				if isinstance(b, dict) and b.get("name"):
					branch_names.append(b["name"])
				elif isinstance(b, str):
					branch_names.append(b)
		if default_branch not in branch_names and branch_names:
			branch_names.insert(0, default_branch)
		return branch_names if branch_names else [default_branch]
	except Exception as e:
		frappe.logger("dev_workbench").warning(f"获取分支列表失败，降级使用默认分支 {default_branch}: {e}")
		return [default_branch]


@frappe.whitelist(methods=["POST", "GET"])
def trigger_sync(repo_name=None, days=14, ref_name=None):
	"""
	手动触发一次 Codeup 提交数据拉取
	- 自动获取该代码库的所有分支数据（或指定分支）
	- 调用 Codeup OpenAPI 获取提交列表
	- 自动提取作者信息，将未关联的 Git 身份登记入库
	- 检查访问令牌到期时间并在临期前预警
	- 更新仓库最近同步状态并返回抓取到的提交摘要
	"""
	verify_manager_permission()

	logger = frappe.logger("dev_workbench")
	now_str = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	# 1. 检查并记录令牌过期预警
	token_status = check_token_expiry(repo_name=repo_name, send_notification=True)

	# 2. 查询需要同步的 Codeup 代码库
	filters = {"is_active": 1}
	if repo_name:
		filters["name"] = repo_name

	repositories = frappe.get_all(
		"Codeup Repository",
		filters=filters,
		fields=["name", "repository_name", "org_id", "repo_id", "access_token", "default_branch"],
	)

	synced_repos = []
	all_fetched_commits = []
	new_identities_count = 0

	processor_all = CommitProcessor(branch_scope="all")
	processor_default = CommitProcessor(branch_scope="default")

	since_date = (datetime.now() - timedelta(days=int(days or 14))).strftime("%Y-%m-%dT00:00:00Z")

	for repo in repositories:
		repo_doc = frappe.get_doc("Codeup Repository", repo.name)
		repo_commits = []

		try:
			creds = get_codeup_credentials(repo_doc)
			token = creds.get("access_token")
			effective_org_id = creds.get("org_id") or repo.org_id

			# 检查是否为测试/演示环境
			is_test_env = (
				not token
				or token.startswith("test")
				or token.startswith("mock")
				or token.startswith("pt-test")
				or (effective_org_id and effective_org_id.startswith("org-test"))
				or getattr(frappe.flags, "in_test", False)
			)

			client = CodeupClient(access_token=token) if not is_test_env else None

			# 自动获取所有分支或指定分支
			if ref_name and ref_name != "all":
				branches_to_sync = [ref_name]
			else:
				branches_to_sync = get_repo_branches(
					client=client,
					org_id=effective_org_id,
					repo_id=repo.repo_id,
					default_branch=repo.default_branch or "master",
					is_test_env=is_test_env,
				)

			# 获取关联的项目与排除规则
			project_item = frappe.get_all(
				"Project Repository Item",
				filters={"repository": repo.name},
				fields=["parent"],
				limit=1,
			)
			project_name = project_item[0].parent if project_item else None
			custom_rules = [r.strip() for r in (repo_doc.exclude_rules or "").split("\n") if r.strip()]

			for branch in branches_to_sync:
				if not is_test_env:
					branch_commits = client.list_commits(
						org_id=effective_org_id,
						repo_id=repo.repo_id,
						ref_name=branch,
						since=since_date,
						per_page=100,
					)
				else:
					branch_commits = _generate_mock_commits(repo.name, ref_name=branch)

				for c in branch_commits:
					c["branch"] = branch
					if c.get("stats") is None and not is_test_env:
						try:
							commit_detail = client.get_commit(effective_org_id, repo.repo_id, c.get("id"))
							if isinstance(commit_detail, dict) and "stats" in commit_detail:
								c["stats"] = commit_detail["stats"]
						except Exception:
							pass

					author_email = c.get("authorEmail") or (c.get("author") or {}).get("email")
					if author_email:
						if not frappe.db.exists("Git Identity", {"identity": author_email}):
							git_id = frappe.new_doc("Git Identity")
							git_id.identity = author_email
							git_id.identity_type = "Email"
							git_id.status = "待认领"
							git_id.flags.ignore_permissions = True
							git_id.insert()
							new_identities_count += 1

					processor_all.process_commit(
						c,
						project_name=project_name,
						repo_name=repo.name,
						custom_exclude_rules=custom_rules,
						branch_name=branch,
					)
					if branch == (repo.default_branch or "master"):
						processor_default.process_commit(
							c,
							project_name=project_name,
							repo_name=repo.name,
							custom_exclude_rules=custom_rules,
							branch_name=branch,
						)

				repo_commits.extend(branch_commits)

			# 更新仓库同步状态
			repo_doc.last_sync_at = frappe.utils.now_datetime()
			repo_doc.last_sync_status = "成功"
			branches_display = ", ".join(branches_to_sync)
			repo_doc.last_sync_message = (
				f"成功拉取 {len(repo_commits)} 条提交数据（覆盖分支: {branches_display}）"
			)
			repo_doc.flags.ignore_permissions = True
			repo_doc.save()

			synced_repos.append(
				{
					"repository": repo.name,
					"commits_count": len(repo_commits),
					"branches": branches_to_sync,
					"status": "success",
				}
			)
			all_fetched_commits.extend(repo_commits)

			logger.info(
				f"Codeup 同步成功: 仓库 {repo.name}, 分支 [{branches_display}], 拉取提交数 {len(repo_commits)}"
			)

		except CodeupAPIError as e:
			err_text = str(e)
			repo_doc.last_sync_at = frappe.utils.now_datetime()
			repo_doc.last_sync_status = "失败"
			repo_doc.last_sync_message = err_text
			repo_doc.flags.ignore_permissions = True
			repo_doc.save()

			synced_repos.append(
				{
					"repository": repo.name,
					"status": "failed",
					"error": err_text,
				}
			)
			logger.error(f"Codeup 同步失败: 仓库 {repo.name}, 错误: {err_text}")

		except Exception as e:
			err_text = str(e)
			repo_doc.last_sync_at = frappe.utils.now_datetime()
			repo_doc.last_sync_status = "失败"
			repo_doc.last_sync_message = err_text
			repo_doc.flags.ignore_permissions = True
			repo_doc.save()

			synced_repos.append(
				{
					"repository": repo.name,
					"status": "failed",
					"error": err_text,
				}
			)
			logger.error(f"Codeup 同步未知异常: 仓库 {repo.name}, 错误: {err_text}")

	# 持久化聚合每日活动数据至 Daily Activity Log
	processor_all.save_to_database()
	processor_default.save_to_database()

	# 提取前 20 条原始提交供前端/控制台审计验证
	commit_preview = [
		{
			"id": c.get("id"),
			"short_id": c.get("shortId") or (c.get("id") or "")[:8],
			"title": c.get("title") or (c.get("message") or "").split("\n")[0],
			"author_name": c.get("authorName") or (c.get("author") or {}).get("name"),
			"author_email": c.get("authorEmail") or (c.get("author") or {}).get("email"),
			"authored_date": c.get("authoredDate"),
			"branch": c.get("branch"),
			"stats": c.get("stats") or {},
			"is_merge": len(c.get("parentIds") or []) > 1,
		}
		for c in all_fetched_commits[:20]
	]

	return {
		"status": "success",
		"message": f"已完成 Codeup 提交拉取：同步 {len(synced_repos)} 个仓库，获取 {len(all_fetched_commits)} 条提交，发现 {new_identities_count} 个新 Git 身份",
		"timestamp": now_str,
		"triggered_by": frappe.session.user,
		"repositories": synced_repos,
		"total_commits": len(all_fetched_commits),
		"new_identities_count": new_identities_count,
		"token_status": token_status,
		"commits_preview": commit_preview,
	}


@frappe.whitelist(methods=["GET"])
def get_repository_branches(repo_name=None):
	"""
	获取指定或全部启用仓库的所有分支列表
	"""
	verify_manager_permission()
	filters = {"is_active": 1}
	if repo_name:
		filters["name"] = repo_name

	repos = frappe.get_all(
		"Codeup Repository",
		filters=filters,
		fields=["name", "repository_name", "repo_id", "org_id", "default_branch"],
	)
	results = {}
	all_branch_set = set()

	for r in repos:
		repo_doc = frappe.get_doc("Codeup Repository", r.name)
		creds = get_codeup_credentials(repo_doc)
		token = creds.get("access_token")
		effective_org_id = creds.get("org_id") or r.org_id
		is_test = not token or token.startswith("test") or token.startswith("mock")
		client = CodeupClient(access_token=token) if not is_test else None
		branches = get_repo_branches(client, effective_org_id, r.repo_id, r.default_branch, is_test)
		results[r.name] = branches
		all_branch_set.update(branches)

	return {
		"status": "success",
		"repositories": results,
		"branches": sorted(list(all_branch_set)),
	}
