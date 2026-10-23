# 05: 提交数据处理

**What to build:**

实现完整的提交数据处理流程：去重、排除 merge commit、按 GitIdentity 映射到成员、应用排除文件规则、计算行数和文件数统计，最后生成 DailyActivityLog 记录。

**Blocked by:** 04

**Status:** resolved

- [x] 实现 commit hash 去重：同一 hash 在多分支上只算一次
- [x] 实现 merge commit 识别和排除：根据 parentIds 长度判断（> 1 为 merge）
- [x] 实现排除文件规则应用：根据 glob 模式排除文件，不计入行数但显示在文件列表
- [x] 实现成员映射：按 commit.author.email 匹配 GitIdentity → ProjectMember；无法匹配放入"未归属"
- [x] 实现每日统计聚合：按成员、日期、项目聚合提交数、行数、文件数
- [x] 实现排除文件统计：内置默认规则（*.lock、dist、build 等），项目可追加自定义规则
- [x] 处理行数未知的情况：标记为"行数未知"，不按 0 计算
- [x] 生成 DailyActivityLog 记录：存储统计数据和原始提交 JSON（供审计）
- [x] 生成"未归属提交"记录：单独统计和存储
- [x] 支持按统计范围筛选：全部分支 vs 仅默认分支
- [x] 创建后端 API `GET /api/activity/daily/<member_id>/<date>`：获取某成员某天的处理后数据

## Answer

### 核心实现概览
1. **提交数据处理核心引擎 (`dev_workbench/services/commit_processor.py`)**:
   - **Commit Hash 去重**：维护会话内已处理 SHA 集合，多分支出现的相同 commit 只计算一次。
   - **Merge Commit 识别与排除**：根据 `parentIds` 长度（`> 1` 为 merge commit）或标准 Merge 提交标题过滤，不计入有效开发提交。
   - **Glob 排除规则引擎**：内置默认规则（`*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `dist/**`, `build/**`, `public/**`, `*.min.js`, `*.min.css`, `node_modules/**`），支持仓库级别自定义 glob 追加。排除文件不计入变更行数，但保留在文件列表中供展示。
   - **作者时间解析与时区规范**：严格按 `authoredDate` 转换为北京时间（UTC+8）对应的工作日期，避免跨天误报。
   - **Git 身份映射与未归属提交**：按 `author.email` 查找 `Git Identity` 并映射到 `Project Member`；未关联身份时标记 `is_unclaimed = 1` 并自动在 `Git Identity` 表中创建待认领记录。
   - **未知行数处理**：当提交未包含 stats 统计时，标记 `lines_unknown = 1`，避免简单归零导致偏差。
   - **每日聚合与持久化**：按 `(member/unclaimed, activity_date, project, branch_scope)` 聚合提交数、新增/删除/总行数、涉及文件数，将原始提交列表序列化为 `raw_json` 存入 `Daily Activity Log` 表，并支持幂等更新合并。

2. **触发同步流水线集成 (`dev_workbench/api/v1/sync.py`)**:
   - 将 `CommitProcessor` 深度集成至 `trigger_sync`，支持按全部分支（`all`）与仅默认分支（`default`）两种统计范围同步生成日志。

3. **每日活动详情查询 API (`dev_workbench/api/v1/activity.py`, `dev_workbench/api/activity.py`)**:
   - 提供 `get_daily_activity(member_id, date, scope)` 接口，校验管理者权限，聚合返回某成员或未归属在指定日期的提交清单、统计数字、AI 摘要及涉及项目。

4. **REST 路由中间件扩展 (`dev_workbench/hooks_middleware.py`)**:
   - 在 `before_request` 钩子中支持 `/api/activity/daily/<member_id>/<date>` 动态路径解析与参数分发。

5. **自动化测试与验证**:
   - 编写自动化测试套件 [test_issue_05.py](file:///d:/project/02-开源项目/frappe_docker/development/frappe-bench/apps/dev_workbench/dev_workbench/tests/test_issue_05.py)，覆盖去重、Merge 排除、Glob 匹配、身份映射、未归属登记、未知行数标记、`DailyActivityLog` 幂等持久化、API 查询与权限拦截。
   - 执行 `bench --site development.localhost execute dev_workbench.tests.test_issue_05.run_issue_05_checks` 验证 **100% 通过**，Issue 04 回归测试亦全部通过。
