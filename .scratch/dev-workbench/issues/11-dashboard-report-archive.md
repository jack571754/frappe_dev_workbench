# 11: 看板 - 日报归档视图

**What to build:**

实现看板的"日报归档"tab，支持历史日报查询、查看过去推送的日报消息、通过飞书链接打开看板。

**Blocked by:** 05, 06, 07, 08

**Status:** resolved

- [x] 创建日报归档 Vue 组件
- [x] 实现日期范围选择器，查询历史日报（过去 N 周）
- [x] 实现日报列表：显示推送日期、推送时间、内容摘要、飞书消息 ID
- [x] 点击日报行，展开详情：完整的卡片消息内容（渲染飞书卡片格式）
- [x] 实现页面内链：日报消息中的"查看详情"链接指向该日的成员日报视图
- [x] 调用后端 API `GET /api/reports/list?from_date=<date>&to_date=<date>`：获取日报列表
- [x] 调用后端 API `GET /api/reports/<report_id>`：获取单个日报详情
- [x] 支持日报重新推送：点击"重新推送"按钮，调用飞书 API 补发消息
- [x] 验证：能查询历史日报，展开详情，点击链接跳转到成员日报视图

## Answer

### 1. 实现概述

已完整交付 Issue 11 的所有目标与功能：
1. **后端报告管理与重发 API (`dev_workbench.api.v1.reports`)**：
   - `GET /api/reports/list?from_date=<date>&to_date=<date>`：按日期区间与状态查询历史 `Daily Report`，规范化返回 `report_date`、`push_time`、`status`、`message_id`、`summary`。
   - `GET /api/reports/<report_id>`：按记录名或日期获取完整日报记录及解析后的飞书卡片 JSON 结构。
   - `POST /api/reports/<report_id>/resend`：根据日报工作日期触发 `send_daily_report` 补发飞书交互卡片，并实时回写 `Daily Report` 的最新推送状态、时间与飞书消息 ID。
   - 严格权限控制：仅系统管理员及研发工作台管理者 (`is_manager=1` 或 `Dev Workbench Manager`) 可调用。
2. **REST 路由中间件转发 (`dev_workbench.hooks_middleware`)**：
   - 将标准 REST 路径 `/api/reports/list`、`/api/reports/<report_id>`、`/api/reports/<report_id>/resend` 统一映射至 Frappe 内部白名单方法。
3. **前端日报归档界面 (`ReportArchivePage.vue`)**：
   - **概览指标卡片**：总归档期数、成功推送期数、失败/草稿期数、最新推送工作日。
   - **日期与状态筛选**：支持起始与结束日期选择，提供快捷选项（近 1 周、近 2 周、近 4 周、全部），以及按状态（Sent、Draft、Failed、Recalled）过滤。
   - **日报归档列表**：以高密度清晰表格呈现工作日期、推送时间、状态 Badge、内容文本摘要、飞书消息 ID，以及操作按钮。
   - **飞书卡片视觉模拟与内链跳转**：支持展开/弹窗以飞书客户端原生风格视觉预览交互卡片（标题栏卡片头模板、项目研发动态、缺勤告警区块、未归属提示、底部操作按钮），同时提供原始 JSON 代码切换；卡片内部包含直达链接与按钮，一键通过 Vue Router 跳转至对应日期的成员日报页面 (`/dashboard/daily-activity?date=YYYY-MM-DD`)。
   - **日报重新推送**：支持在列表或卡片弹窗中点击"重新推送"，调用后端接口补发飞书消息并实时刷新推送状态。
4. **编译与自动化验证**：
   - 前端成功通过 Vite 编译，产物写入 `public/workbench/`。
   - 编写 `test_issue_11.py` 覆盖列表、详情、重发、权限校验及 REST 路由，测试通过率 100%。
