# 01: App 骨架和数据模型

**What to build:**

创建 `dev_workbench` Frappe app，定义所有核心 DocType，使管理者能在 Frappe Desk 中查看、创建和编辑这些模型。这是整个工作台的数据基础。

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] 创建 dev_workbench app 结构（使用 bench new-app 或从 PSP 复制模板）
- [x] 定义 Project DocType：名字、描述、是否启用等基础字段
- [x] 定义 ProjectMember DocType：全局成员表，关联飞书用户（user_id）和 open_id
- [x] 定义 GitIdentity DocType：邮箱或用户名、关联的 ProjectMember、状态（已认领/待认领）
- [x] 定义 CodeupRepository DocType：仓库名、Codeup org id、repo id、个人令牌、排除规则（多行）
- [x] 定义 DailyActivityLog DocType：成员、日期、项目、提交数、行数、文件数、提交摘要、原始 JSON 数据
- [x] 定义 DailyReport DocType：工作日期、推送时间、飞书消息 id、内容摘要
- [x] Project 中添加 Table 字段 project_repositories（关联 CodeupRepository）
- [x] ProjectMember 中添加 Table 字段 git_identities（关联 GitIdentity）
- [x] 设置基础权限：只有飞书通讯录中被标记"管理者"的人能访问这个 app
- [x] 在 Frappe Desk 验证所有 DocType 都能创建、读取、更新、删除

## Answer

已完成 `dev_workbench` 应用的搭建与数据模型初始化：

1. **应用骨架**：
   - 在 `/workspace/development/frappe-bench/apps/dev_workbench` 完成了 `dev_workbench` app 的骨架生成与可编辑安装 (`bench install-app dev_workbench`)。
   - 并在站点 `development.localhost` 完成了安装与数据库同步。

2. **核心 DocType 及子表**：
   - `Project`：包含 `project_name`、`description`、`is_active` 以及 `project_repositories`（关联 `Project Repository Item`）。
   - `Codeup Repository`：包含 `repository_name`、`org_id`、`repo_id`、`access_token`、`default_branch`、`exclude_rules`、`is_active`。
   - `Project Member`：包含 `member_name`、`user_id`、`open_id`、`email`、`mobile`、`department`、`is_manager`、`is_active` 以及 `git_identities`（关联 `Project Member Git Identity`）。
   - `Git Identity`：包含 `identity`、`identity_type`、`member`、`status`（`待认领`/`已认领`）、`claimed_at`、`claimed_by`，支持双向自动同步。
   - `Daily Activity Log`：包含 `member`、`activity_date`、`project`、`commit_count`、`lines_added`、`lines_deleted`、`total_lines`、`file_count`、`branch_scope`、`is_unclaimed`、`summary`、`raw_json`。
   - `Daily Report`：包含 `report_date`、`push_time`、`message_id`、`status`、`summary`、`content`。
   - `Absence Exemption`：预置请假豁免模型，含合法性校验。

3. **权限与 Desk 工作区**：
   - 创建了 `Dev Workbench Manager` 业务管理者角色。
   - 在 `dev_workbench/setup_roles.py` 中实现了 DocType 权限控制，并在 `Project Member` 维护 `is_manager` 标记时自动联动分配该角色。
   - 在 Frappe Desk 中配置并同步了「研发工作台」Workspace，包含项目、代码库、成员、身份、活动日志和日报等快捷卡片。

4. **全量 CRUD 自动化验证**：
   - 编写并执行了自动化测试套件 `dev_workbench.tests.test_doctype_crud.run_all_checks`，全部通过（100% 验证通过创建、更新、自动计算与级联同步、读取以及删除操作）。


