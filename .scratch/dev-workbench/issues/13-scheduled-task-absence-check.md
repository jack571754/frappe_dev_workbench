# 13: 定时任务 - 缺勤检查

**What to build:**

实现 Frappe Scheduled Task，每个工作日晚上执行缺勤判断，生成缺勤记录，供日报推送和看板展示。

**Blocked by:** 06

**Status:** resolved

- [x] 创建 Scheduled Task 类，命名为 `check_absence` 或类似
- [x] 配置执行频率：每个工作日晚上（例如 18:00）
- [x] 实现任务逻辑：
  - 遍历所有 ProjectMember
  - 调用缺勤判断模块：检查过去 2 个工作日的 DailyActivityLog
  - 应用豁免规则：检查 AbsenceExemption 表
  - 生成或更新缺勤记录（可在 DailyActivityLog 中添加缺勤标记，或单独表）
- [x] 错误处理：单个成员检查失败不中断其他成员
- [x] 记录检查时间戳，在日志中记录缺勤成员列表
- [x] 验证：任务能定时运行，缺勤标记被正确生成，豁免规则生效

## Answer

### 1. 实现概述

已完全实现并验证 Issue 13 要求的定时缺勤检测任务：
1. **定时任务函数 (`dev_workbench.tasks.absence.check_absence`)**：
   - **工作日判定与回溯**：基于中国法定节假日/调休工作日日历，识别当前核查日是否为工作日；自动提取过去连续 2 个工作日 (`consecutive_count=2`) 作为检测时间窗口。
   - **全员提交状态核查**：遍历所有激活状态的 `Project Member`，核查其在连续工作日窗口内是否存在有效的 `Daily Activity Log`（且 `commit_count > 0`）。
   - **请假豁免规则判定**：对连续无提交成员核查 `Absence Exemption` 表是否存在激活且日期覆盖核查区间的请假记录；若存在则自动标注 `is_exempted=1`，状态流转为"已豁免"，并关联请假原因；未豁免成员则标记 `is_exempted=0`，状态流转为"待跟进"。
   - **活跃提交自动纠错**：若成员在补交提交后重新触发检测，系统自动清除撤销历史缺勤记录，保证数据一致性。
   - **单成员故障隔离**：每个成员处理采用独立异常保护，单个成员查询或写入异常不中断其余成员的检测。
   - **系统日志持久化**：使用 `frappe.logger("dev_workbench")` 记录核查总人数、缺勤成员数、待跟进成员列表、已豁免成员列表及检测时间戳。
2. **Frappe Scheduler 注册 (`hooks.py`)**：
   - 在 `scheduler_events` 中注册 `daily` 以及 `cron: {"0 18 * * 1-5"}`，确保每个工作日傍晚准时自动运行。
3. **自动化测试验证 (`test_issue_13.py`)**：
   - 验证出勤排除、无豁免"待跟进"生成、请假备案"已豁免"流转、补充提交自动撤销、单成员异常隔离、以及 hooks 调度配置，测试通过率 100%。
