# 14: 定时任务 - 飞书日报推送

**What to build:**

实现 Frappe Scheduled Task，每个工作日早上 9 点自动推送飞书日报，汇总前一工作日的代码活动和缺勤信息。

**Blocked by:** 08

**Status:** resolved

- [x] 创建 Scheduled Task 类，命名为 `push_daily_report` 或类似
- [x] 配置执行频率：每个工作日早上 9 点
- [x] 实现任务逻辑：
  - 确定前一工作日（排除周末和法定节假日）
  - 调用日报生成逻辑：聚合该日的 DailyActivityLog 和缺勤记录
  - 构建飞书卡片消息
  - 调用飞书应用机器人 API，发送给管理者（receive_id_type: open_id）
  - 保存推送结果到 DailyReport 表（推送时间、飞书消息 id、内容摘要）
- [x] 错误处理：推送失败时重试，记录错误日志
- [x] 如果前一天是休息日或假期，跳过推送
- [x] 验证：任务能定时运行，飞书消息被成功推送，DailyReport 被记录

## Answer

### 1. 实现概述

已完全实现并验证 Issue 14 要求的飞书效能日报工作日早晨定时推送任务：
1. **定时推送任务函数 (`dev_workbench.tasks.report.push_daily_report`)**：
   - **智能节假日识别与跳过**：在每个调度周期自动判断当日是否为工作日；若当日为休息日或法定节假日（且未显式指定 `force=True`），自动跳过推送避免打扰团队管理者。
   - **自动确定前一工作日**：调用 `workday_service.get_default_report_date()` 排除周末和法定节假日，精准锁定前一真实工作日作为待汇总日期。
   - **日报数据聚合与交互卡片构造**：聚合当日各项目成员的提交数、变更代码行、文件数、AI 生成的 100 字内工作摘要、连续 2 工作日缺勤告警区块、未归属提交认领警示、以及跳转至对应工作台看板的直达操作按钮。
   - **飞书卡片投递**：向所有激活且配置了 `open_id` 的管理者 (`is_manager=1`) 发送飞书 Interactive Card（`receive_id_type="open_id"`），具备 429 自动限流退避与重试机制。
   - **持久化归档至 Daily Report**：写入 `report_date`、`push_time`、`status` ("Sent" 或 "Failed")、飞书 `message_id`、`summary` 与完整的卡片 JSON 内容，供历史归档查询与补发。
   - **异常容错与系统日志**：捕获单次推送或网络异常，持久化记录到 Frappe Error Log，不中断调度器执行。
2. **Frappe Scheduler 注册 (`hooks.py`)**：
   - 在 `scheduler_events` 中注册 `daily` 以及 `cron: {"0 9 * * 1-5"}`，实现工作日早晨 09:00 定时唤醒推送。
3. **自动化测试验证 (`test_issue_14.py`)**：
   - 验证非工作日跳过逻辑、交互卡片结构、管理者目标路由 (`open_id`)、`Daily Report` 状态与字段回写、异常捕获以及 hooks 调度配置，测试通过率 100%。
