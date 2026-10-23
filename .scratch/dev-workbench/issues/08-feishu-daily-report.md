# 08: 飞书日报推送

**What to build:**

实现飞书应用机器人集成，生成交互卡片日报消息（包含项目分栏、成员摘要、缺勤列表、未归属提交数），支持手动推送和定时推送。

**Blocked by:** 05, 06, 07

**Status:** resolved

- [x] 集成飞书应用机器人：使用 tenant_access_token 调用发送消息接口（receive_id_type: open_id）
- [x] 实现日报消息卡片格式：
  - 前一工作日的日期
  - 按项目分栏，每栏包含：项目名、成员的提交摘要（提交数、行数、文件数 + AI 摘要）
  - 单独一栏列出缺勤成员（醒目标记）
  - "未归属提交"数量提示
  - 页面链接（指向该天的详细看板）
- [x] 实现日报生成逻辑：聚合前一工作日的 DailyActivityLog 和缺勤记录
- [x] 创建后端 API `POST /api/feishu/test`：管理者手动推送一条测试日报消息
- [x] 创建 DailyReport 记录：存储推送时间、飞书消息 id、内容摘要
- [x] 错误处理：推送失败时记录错误，重试机制
- [x] 验证：能成功手动推送一条日报消息到飞书，格式正确

## Answer

### 1. 架构与功能实现

- **飞书应用机器人客户端 (`dev_workbench/services/feishu_client.py`)**:
  - `FeishuClient`：实现基于飞书开放平台 OpenAPI 的应用机器人鉴权与消息发送。
  - 支持 `tenant_access_token` 自动获取、本地 TTL 缓存与过期自动刷新机制；
  - 凭据获取优先级：`Dev Workbench Settings` -> `Social Login Key (provider='feishu')` -> 环境变量 `FEISHU_APP_ID/FEISHU_APP_SECRET`。
  - 支持 `send_interactive_card(receive_id, card_dict, receive_id_type='open_id')` 发送交互卡片，支持 429 限流指数退避与重试机制（默认最多 3 次）。
- **飞书交互卡片构造器 (`dev_workbench/services/feishu_card_builder.py`)**:
  - `build_daily_report_card` 严格遵循 Issue 08 规范构造卡片 JSON：
    1. 顶部 Header：工作日期（前一工作日）与总体活跃概览；
    2. 按项目分栏（Projects Section）：分栏列出各项目名称，展示各成员当日提交数、代码变更行数、涉及文件数，并附带 AI 生成的一句话摘要（引用格式）；
    3. 缺勤提醒分栏（Absence Section）：醒目标记连续 2 工作日无提交成员，并区分“待跟进”与“已请假豁免”及请假原因；
    4. 未归属提交警示（Unclaimed Hint）：若有未归属提交，提示管理者前往工作台认领 Git 身份；
    5. 详细看板链接（Action Button）：一键跳转至工作台对应日期的看板详细页面 `/dev-workbench/dashboard/daily-activity?date=...`。
- **日报数据聚合与推送服务 (`dev_workbench/services/feishu_report_service.py`)**:
  - `build_daily_report_payload(report_date)`：自动计算前一工作日，聚合当日全部分支提交活动日志，并联动缺勤判定结果。
  - `send_daily_report(report_date, target_open_id)`：向管理者推送卡片消息，并持久化到 `Daily Report` DocType。
  - 记录 `report_date`、`push_time`、`status`（`Sent` / `Failed` / `Draft`）、`message_id`、`summary` 与完整 `content` JSON。
- **REST API 与路由分发 (`api/v1/feishu.py`, `hooks_middleware.py`)**:
  - `POST /api/feishu/test`：支持管理者手动向指定或默认管理者 open_id 发送测试日报。
  - `GET /api/feishu/preview`：提供卡片 JSON 与数据结构实时预览接口。
  - 严格执行管理者权限验证（`Dev Workbench Manager` / `System Manager` / `is_manager=1`）。

### 2. 自动化测试与验证

- 自动化测试用例位于 `dev_workbench/tests/test_issue_08.py`。
- 测试覆盖：
  1. FeishuClient `tenant_access_token` 获取与缓存；
  2. 交互卡片元素完整性（项目分栏、成员统计+AI摘要、缺勤提醒、未归属提示、看板链接）；
  3. 日报数据聚合引擎计算；
  4. 飞书卡片推送与 `Daily Report` 数据表记录（`push_time`、`message_id`、`status`、`content`）；
  5. 429 限流退避重试与失败容错；
  6. `POST /api/feishu/test` 与 `/api/feishu/preview` 权限拦截与路由转发。
- 执行 `bench --site development.localhost execute dev_workbench.tests.run_all_tests.run_all_workbench_checks`，全量测试套件（Issues 05 ~ 08）全部 100% 通过！


