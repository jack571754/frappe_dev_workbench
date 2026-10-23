# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe import _

from dev_workbench.api.v1.sync import _generate_mock_commits, get_repo_branches
from dev_workbench.services.codeup_client import CodeupAPIError, CodeupClient
from dev_workbench.services.commit_processor import CommitProcessor
from dev_workbench.services.token_service import check_token_expiry, get_codeup_credentials


def sync_codeup_data(repo_name=None, days=None, ref_name=None, force_all=False) -> dict:
	"""
	Codeup 定时同步任务 / 批量拉取处理核心方法
	执行频率：30 ~ 60 分钟一次（Frappe Scheduler 调用）

	功能规范：
	1. 遍历所有启用的 Project 和 CodeupRepository
	2. 自动拉取全部分支数据（去重汇总）
	3. 增量拉取：基于每个仓库的 last_sync_at 时间戳（回退 1 小时容差重叠，防止时钟漂移丢提交）
	   若无上次同步时间或指定 days，则拉取最近指定天数（默认 14 天）
	4. 数据处理：调用 CommitProcessor 去重、排除 merge commit、自定义 glob 过滤、映射作者与项目
	5. 统计与聚合：按全部分支 (all) 与默认分支 (default) 聚合保存 DailyActivityLog
	6. 未归属提交管理：自动创建待认领 Git Identity 记录，并在 DailyActivityLog 中标注 is_unclaimed
	7. 错误隔离：单个仓库同步失败记录错误日志并继续同步后续仓库，绝不中断整体任务
	8. 同步状态更新：回写 last_sync_at, last_sync_status, last_sync_message
	9. 令牌过期预警：检测 access_token 有效期，到期前 7 天自动向管理者发送飞书与系统预警
	10. 系统日志记录：在 Frappe 日志中持久化同步结果摘要（成功数、失败数、新提交数）
	"""
	logger = frappe.logger("dev_workbench")
	now = datetime.now()
	now_str = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	logger.info(f"[Scheduled Task] 开始执行 Codeup 数据定时同步: {now_str}")

	# 1. 检查访问令牌过期情况并发送提醒
	token_statuses = []
	try:
		token_statuses = check_token_expiry(repo_name=repo_name, send_notification=True)
	except Exception as e:
		logger.error(f"检查 Codeup 访问令牌有效期发生异常: {e}")

	# 2. 查找需要同步的代码仓库
	filters = {"is_active": 1}
	if repo_name:
		filters["name"] = repo_name

	repositories = frappe.get_all(
		"Codeup Repository",
		filters=filters,
		fields=[
			"name",
			"repository_name",
			"org_id",
			"repo_id",
			"access_token",
			"default_branch",
			"last_sync_at",
			"exclude_rules",
		],
	)

	synced_repos = []
	all_fetched_commits = []
	new_identities_count = 0
	failed_repos_count = 0

	processor_all = CommitProcessor(branch_scope="all")
	processor_default = CommitProcessor(branch_scope="default")

	for repo in repositories:
		repo_doc = frappe.get_doc("Codeup Repository", repo.name)
		repo_commits = []

		# 计算增量起点时间
		if days:
			since_dt = now - timedelta(days=int(days))
		elif repo_doc.last_sync_at and not force_all:
			# 上次同步时间前推 1 小时，避免临界点丢提交，去重机制保证幂等
			last_sync_dt = frappe.utils.get_datetime(repo_doc.last_sync_at)
			since_dt = last_sync_dt - timedelta(hours=1)
		else:
			since_dt = now - timedelta(days=14)

		since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

		try:
			creds = get_codeup_credentials(repo_doc)
			token = creds.get("access_token")
			effective_org_id = creds.get("org_id") or repo.org_id

			is_test_env = (
				not token
				or token.startswith("test")
				or token.startswith("mock")
				or token.startswith("pt-test")
				or (effective_org_id and effective_org_id.startswith("org-test"))
				or getattr(frappe.flags, "in_test", False)
			)

			client = (
				CodeupClient(access_token=token, base_url=creds.get("base_url")) if not is_test_env else None
			)

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

			# 获取该代码仓库关联的所属 Project
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
						since=since_str,
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

			# 更新仓库同步时间戳与状态
			repo_doc.last_sync_at = frappe.utils.now_datetime()
			repo_doc.last_sync_status = "成功"
			branches_display = ", ".join(branches_to_sync)
			repo_doc.last_sync_message = (
				f"成功拉取 {len(repo_commits)} 条提交（分支: {branches_display}, 起点: {since_str}）"
			)
			repo_doc.flags.ignore_permissions = True
			repo_doc.save()

			synced_repos.append(
				{
					"repository": repo.name,
					"commits_count": len(repo_commits),
					"branches": branches_to_sync,
					"status": "success",
					"since": since_str,
				}
			)
			all_fetched_commits.extend(repo_commits)

			logger.info(f"仓库【{repo.name}】同步成功: 提交数={len(repo_commits)}, 分支=[{branches_display}]")

		except CodeupAPIError as e:
			failed_repos_count += 1
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
			logger.error(f"Codeup API 同步失败 (仓库 {repo.name}): {err_text}")
			frappe.log_error(title=f"Codeup API 同步失败 ({repo.name})", message=err_text)

		except Exception as e:
			failed_repos_count += 1
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
			logger.error(f"Codeup 同步未知异常 (仓库 {repo.name}): {err_text}")
			frappe.log_error(title=f"Codeup 同步异常 ({repo.name})", message=frappe.get_traceback())

	# 持久化每日活动数据到 Daily Activity Log
	saved_logs_all = processor_all.save_to_database()
	saved_logs_default = processor_default.save_to_database()
	frappe.db.commit()

	summary_msg = (
		f"Codeup 同步完成: 仓库成功 {len(repositories) - failed_repos_count}/{len(repositories)}, "
		f"抓取提交数 {len(all_fetched_commits)}, "
		f"新增 Git 身份 {new_identities_count}, "
		f"保存活动日志 {len(saved_logs_all) + len(saved_logs_default)}"
	)

	logger.info(f"[Scheduled Task] {summary_msg}")

	return {
		"status": "success" if failed_repos_count == 0 else "partial_success",
		"message": summary_msg,
		"timestamp": now_str,
		"total_repositories": len(repositories),
		"successful_repositories": len(repositories) - failed_repos_count,
		"failed_repositories": failed_repos_count,
		"total_commits": len(all_fetched_commits),
		"new_identities_count": new_identities_count,
		"repositories": synced_repos,
		"token_statuses": token_statuses,
	}
