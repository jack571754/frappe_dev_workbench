# 06: 缺勤判断

**What to build:**

实现工作日日历计算、连续 2 个工作日无提交检测、豁免规则应用，生成缺勤记录供日报和看板展示。

**Blocked by:** 05

**Status:** resolved

- [x] 实现工作日日历计算：根据国家法定节假日日历确定工作日（可用飞书日历 API 或内置配置）
- [x] 实现连续 2 工作日无提交检测：检查 DailyActivityLog，过去 2 个工作日都没有提交记录则标记缺勤
- [x] 实现豁免规则应用：检查 AbsenceExemption 表，如果有匹配的豁免记录则不算缺勤
- [x] 创建缺勤记录表（或在 DailyActivityLog 中添加字段）：记录缺勤状态和豁免原因
- [x] 创建后端 API `GET /api/absence/list/<date>`：获取某日的缺勤成员列表
- [x] 创建后端 API `POST /api/member/claim-identity`：管理者认领 Git 身份后，重新计算该成员过去 N 天的缺勤状态

## Answer

### 1. 架构与功能实现

- **DocType: Absence Record (缺勤记录)**:
  - 路径：`apps/dev_workbench/dev_workbench/dev_workbench/doctype/absence_record/`
  - 关键字段：`member` (Link Project Member), `member_name`, `check_date`, `consecutive_workdays`, `is_exempted`, `exemption_reason`, `status` (待跟进 / 已豁免 / 已撤销), `remarks`。已执行 `bench migrate` 同步至 MariaDB。
- **法定节假日与工作日服务 (`dev_workbench/services/workday_service.py`)**:
  - 内置 2025/2026/2027 年国务院公布的中国法定节假日（元旦、春节、清明、劳动、端午、中秋、国庆）及对应调休补班周末规则。
  - 支持 `is_workday(date)`、`get_previous_workdays(ref_date, count=2, include_ref_date=True)` 及跨周末区间查询。
- **缺勤判定与豁免引擎 (`dev_workbench/services/absence_service.py`)**:
  - `check_absences(check_date, consecutive_count=2)`：精确拉取基准日前 N 个工作日，检查激活成员在此期间的 `Daily Activity Log` 提交活动。
  - 自动匹配 `Absence Exemption`（请假、出差等豁免区间），若命中且生效则自动打标 `is_exempted=1, status='已豁免'`，否则生成 `is_exempted=0, status='待跟进'` 待管理者跟进。
  - 支持幂等更新与历史重算。
- **Git 身份认领回溯与误报撤销 (`recalculate_member_absence_after_claim`)**:
  - 当管理者在 `POST /api/member/claim-identity` 认领 Git 身份后，中间件与认领服务自动触发历史未归属日志重新归属该成员。
  - 随后自动回溯过去 30 天内该成员的缺勤记录，若重新计算发现已满足提交条件，自动撤销或删除历史误报缺勤记录。
- **REST API 与路由分发 (`api/v1/absence.py`, `hooks_middleware.py`)**:
  - `GET /api/absence/list/<date>?include_exempted=1`：严格验证调用者管理者权限（Administrator / System Manager / Dev Workbench Manager / is_manager=1），支持过滤豁免与非豁免。
  - 中间件统一映射 `/api/absence/list/<date>` REST 路径到后端白名单方法。

### 2. 自动化测试与验证

- 自动化测试用例位于 `dev_workbench/tests/test_issue_06.py`。
- 测试覆盖：
  1. 法定假日、调休补班及跨周末工作日日历算法；
  2. 连续 2 个工作日无提交检测与 Absence Record 记录生成；
  3. 请假豁免规则自动匹配与状态流转；
  4. 认领 Git 身份后历史提交回溯与误报缺勤记录自动撤销；
  5. API 权限拦截（普通用户 403 / 抛出 PermissionError）与 REST 路由分发。
- 通过命令 `bench --site development.localhost execute dev_workbench.tests.test_issue_06.run_issue_06_checks`，测试 100% 通过且完全清理测试数据。

