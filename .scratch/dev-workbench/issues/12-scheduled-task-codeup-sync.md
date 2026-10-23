# 12: 定时任务 - Codeup 同步

**What to build:**

实现 Frappe Scheduled Task，每 30 到 60 分钟自动拉取 Codeup 提交数据、处理、生成 DailyActivityLog，保证数据持续更新。

**Blocked by:** 04, 05

**Status:** resolved

- [x] 创建 Scheduled Task 类，命名为 `sync_codeup_data` 或类似
- [x] 配置执行频率：30 到 60 分钟执行一次
- [x] 实现任务逻辑：
  - 遍历所有启用的 Project 和 CodeupRepository
  - 调用 Codeup API ListCommits，获取上次同步以后的新提交
  - 调用数据处理模块：去重、排除 merge commit、映射、统计
  - 更新 DailyActivityLog（新增或更新）
  - 生成"未归属提交"记录
- [x] 错误处理：单个仓库失败不中断其他仓库的同步；记录错误日志
- [x] 记录同步时间戳，下次同步时以此为起点（避免重复拉取）
- [x] 实现令牌过期提醒：检查令牌有效期，过期前 7 天飞书通知管理者
- [x] 在 Frappe 系统日志中记录每次同步的结果（成功数、失败数、新提交数）
- [x] 验证：任务能定时运行，DailyActivityLog 被正确更新

## Answer

### 1. 实现概述

已完全实现并验证 Issue 12 要求的 Codeup 自动化定时增量同步任务：
1. **定时任务函数 (`dev_workbench.tasks.sync.sync_codeup_data`)**：
   - **增量拉取机制**：基于每个激活仓库的 `last_sync_at` 字段作为 `since` 同步起点（前推 1 小时容差窗口防止时钟漂移，配合 `CommitProcessor` 的 SHA-1 幂等去重保证零漏算与零重复）；首次同步或指定 `days` 时默认回溯 14 天。
   - **流水线数据处理**：调用 `CommitProcessor` 执行 Merge Commit 过滤、排除规则匹配（默认锁文件/产物 + 仓库自定义 Glob 规则）、成员 Git 身份映射（Email/Name）、代码变更量统计（新增、删除、总行数、文件数），并按全部分支 (`branch_scope="all"`) 与仅默认分支 (`branch_scope="default"`) 写入/增量更新 `Daily Activity Log`。
   - **未归属提交管理**：自动为新邮箱创建状态为"待认领"的 `Git Identity`，并在 `Daily Activity Log` 中自动标注 `is_unclaimed=1`。
   - **多仓故障隔离**：使用单独的 `try...catch` 包裹单个仓库处理逻辑，单个仓库发生 4xx/5xx/网络超时等异常时，自动将该仓库状态更新为"失败"并记录到 Frappe Error Log，同时继续后续代码库的同步，确保任务具备高可用容错能力。
   - **同步时间戳与状态回写**：成功时更新 `repo_doc.last_sync_at`、`last_sync_status="成功"` 与拉取条数摘要。
   - **访问令牌临期预警**：同步时自动调用 `check_token_expiry(send_notification=True)` 检查各仓库凭证有效期，在剩余 <= 7 天时自动通过飞书通知与系统通知预警管理者。
   - **系统日志持久化**：使用 `frappe.logger("dev_workbench")` 记录详细同步事件与结果统计（成功仓库数、失败仓库数、拉取提交数、新增 Git 身份数、写入日志条数）。
2. **Frappe Scheduler 注册 (`hooks.py`)**：
   - 在 `scheduler_events` 中配置 `hourly` 以及 `cron: {"*/30 * * * *"}` 调度规则，支持系统每 30 ~ 60 分钟自动唤起执行。
3. **飞书文本消息与管理者预警 (`feishu_client.py`)**：
   - 增加 `send_text_message` 与 `send_feishu_message_to_managers` 方法，满足令牌到期与异常直接推送管理者飞书的需求。
4. **自动化验证 (`test_issue_12.py`)**：
   - 包含首次同步、增量防漏重叠、异常隔离、未归属标记、7天令牌预警、以及 hooks 调度事件注册校验，测试通过率 100%。
