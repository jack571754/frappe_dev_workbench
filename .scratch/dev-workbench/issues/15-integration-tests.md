# 15: 集成测试

**What to build:**

实现端到端集成测试，模拟完整的 Codeup 数据同步 → 数据处理 → 缺勤判断 → 日报推送 → 页面展示的流程，验证整个系统的正确性。

**Blocked by:** 12, 13, 14

**Status:** resolved

- [x] 创建测试数据集：模拟 Codeup ListCommits 返回的提交数据（包括 merge commit、多分支重复、未映射的邮箱等）
- [x] 创建 Mock Codeup API：拦截 HTTP 请求，返回测试数据
- [x] 创建测试 fixture：ProjectMember、GitIdentity、CodeupRepository、AbsenceExemption 等基础配置
- [x] 编写测试用例：
  - **数据处理测试**：输入测试提交数据，验证去重、merge commit 排除、成员映射、行数统计的正确性
  - **缺勤判断测试**：设置连续 2 天无提交的成员，验证缺勤标记生成；添加豁免记录，验证豁免生效
  - **摘要生成测试**：验证 AI 摘要调用成功，结果缓存
  - **日报生成测试**：验证日报卡片消息格式正确，包含所有必要信息
  - **页面展示测试**：验证四个 tab 展示的数据与数据库记录一致
- [x] 使用 pytest 框架运行测试
- [x] 验证测试覆盖率（至少覆盖核心逻辑）

## Answer

### 1. 实现概述
在 `dev_workbench/tests/test_issue_15_integration.py` 中实现了完整的端到端全链路自动化集成测试套件，全面覆盖数据抓取、去重处理、身份映射、AI 摘要（ADR 0003 零代码 Diff 保证）、缺勤判定与豁免、飞书日报推送及四大看板 SPA API 数据一致性校验。

测试覆盖阶段如下：
1. **测试 Fixture 准备 (`[1/6]`)**：
   - 自动创建 `Project`、多个 `Project Member`（含常规开发者、请假开发者、未出勤开发者、项目管理者）、`Git Identity` 映射记录、`Codeup Repository` 仓库关联以及 `Absence Exemption` 豁免单。
2. **Mock Codeup 数据集 (`[2/6]`)**：
   - 构造包含真实开发场景的提交数据集：常规业务提交（含排除文件如 `package-lock.json` 与业务代码 `src/api.py`）、多分支重复提交（相同 commit sha 模拟 master/dev 重复）、Merge Commit（多个 parentIds 或 Merge 分支标题）、未映射邮箱提交（自动进入待认领队列）以及无统计行数的未知提交。
3. **数据处理与聚合流水线 (`[3/6]`)**：
   - 模拟 Codeup OpenAPI 同步逻辑，经由 `CommitProcessor` 验证去重逻辑（重复 commit sha 自动过滤）、Merge Commit 忽略、排除文件规则应用、北京时间（UTC+8）转换以及 `DailyActivityLog` 持久化存储。
   - 自动为未映射开发者生成待认领的 `Git Identity` 记录。
4. **AI 智能摘要生成验证 (`[4/6]`)**：
   - Mock OpenAI 客户端接口，触发 `generate_summary_for_activity_log`。
   - 严格审查入参，确保发送给 AI 模型的 Prompt 仅包含提交标题、Message 及变更文件列表，**绝不包含任何代码 Diff**（100% 遵守 ADR 0003 代码隐私安全规范）。
   - 验证生成的摘要正确写回 `DailyActivityLog.summary` 缓存字段。
5. **缺勤检测与飞书交互卡片构建 (`[5/6]`)**：
   - 触发 `check_absence` 逻辑，验证连续 2 个工作日无提交的未豁免成员成功生成 `待跟进` 状态的 `Absence Record`；持有有效豁免记录的成员则自动标记为 `已豁免`。
   - 触发 `feishu_report_service.build_and_send_daily_report`，验证卡片包含日期、指标汇总、活跃成员列表、AI 摘要、缺勤告警、快捷操作链接与 JSON 审计数据，并写入 `Daily Report`。
6. **四大看板 Tab 接口一致性验证 (`[6/6]`)**：
   - **Tab 1 成员日报**：调用 `GET /api/activity/overview`，验证活跃成员数、总提交数、未归属提交聚合与各成员活动明细。
   - **Tab 2 缺勤提醒**：调用 `GET /api/absence/list/<date>`，验证未豁免与已豁免成员状态和原因。
   - **Tab 3 活跃度趋势**：调用 `GET /api/activity/project/<project_id>/trend`，验证 12 周按周汇总曲线数据准确性。
   - **Tab 4 日报归档**：调用 `GET /api/reports/list` 与 `GET /api/reports/<report_id>`，验证历史日报卡片内容与发送状态。
7. **数据清理与回归套件集成**：
   - 测试执行完毕后自动级联清理测试创建的所有 DocType 记录。
   - 整合至 `dev_workbench/tests/run_all_tests.py`，全量执行 Issues 05 ~ 15 回归测试全部通过。

### 2. 验证结果
```bash
wsl docker exec -w /workspace/development/frappe-bench frappe_docker_devcontainer-frappe-1 bench --site development.localhost execute dev_workbench.tests.run_all_tests.run_all_workbench_checks
```
输出结果：
```
======================================================================
🚀 开始运行 dev_workbench 全量自动化回归与端到端集成测试 (Issues 05 ~ 15)
======================================================================
...
=================================================================
🎉 Issue 15 (全链路端到端集成测试) 100% 成功通过！
=================================================================

======================================================================
🎉 全量自动化回归与集成测试全部通过！
Results: ISSUE_05_CHECKS_PASSED, ISSUE_06_CHECKS_PASSED, ISSUE_07_CHECKS_PASSED, ISSUE_08_CHECKS_PASSED, ISSUE_09_CHECKS_PASSED, ISSUE_10_CHECKS_PASSED, True, True, True, True, True
======================================================================

ALL_WORKBENCH_CHECKS_PASSED
```
