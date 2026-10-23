# Effort Map: Dev Workbench (研发工作台)

Status: completed

## Notes
- 研发工作台 (`dev_workbench`) 为独立全栈 Frappe App，与 PSP (Product Sales Planning) 同 site 协同运行。
- 从 Codeup OpenAPI 定时同步代码提交，经过去重、Merge 过滤、Glob 排除规则及 UTC+8 时区转换聚合为每日活动日志。
- 支持基于国家法定节假日日历的连续 2 工作日缺勤判定与请假豁免流转。
- 采用符合 ADR 0003 规范（严格零代码 Diff）的 AI 智能提交摘要生成。
- 支持飞书应用机器人交互卡片工作日定时向管理者私聊推送及看板详情跳转。
- 提供基于 Vue 3 + Tailwind CSS 的高密度 SPA 管理看板（成员日报、缺勤提醒、项目活跃度趋势、历史日报归档、配置中心）。

## Decisions So Far
- **[01-app-scaffold-and-doctypes](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/01-app-scaffold-and-doctypes.md)**: 建立 8 个核心 DocType、角色权限（Dev Workbench Manager）与 Desk 工作区。
- **[02-app-scaffold-and-first-page](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/02-app-scaffold-and-first-page.md)**: 初始化 Vue 3 SPA 脚手架与布局，支持全局分支统计范围切换。
- **[03-config-pages](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/03-config-pages.md)**: 实现飞书成员同步、Git 身份认领与 SPA 配置页面。
- **[04-codeup-integration](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/04-codeup-integration.md)**: 实现 Codeup OpenAPI 客户端、访问令牌到期检查与手动同步接口。
- **[05-commit-data-processing](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/05-commit-data-processing.md)**: 实现 CommitProcessor（去重、Merge 排除、Glob 行数排除与每日日志聚合持久化）。
- **[06-absence-judgment](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/06-absence-judgment.md)**: 实现节假日日历服务、连续 2 工作日缺勤检测、豁免记录流转与认领回溯。
- **[07-ai-summary](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/07-ai-summary.md)**: 严格执行 ADR 0003（零代码 Diff）AI 提交摘要生成、缓存与后台异步队列。
- **[08-feishu-daily-report](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/08-feishu-daily-report.md)**: 实现飞书交互卡片消息构建器、429 指数退避重试与 Daily Report 状态归档。
- **[09-dashboard-daily-activity](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/09-dashboard-daily-activity.md)**: 交付 DailyActivityPage 成员日报视图及后端总览聚合 API。
- **[10-dashboard-absence-activity](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/10-dashboard-absence-activity.md)**: 交付 AbsenceActivityPage 缺勤跟进、快速豁免与 ProjectTrendPage 12 周活跃度 SVG 曲线。
- **[11-dashboard-report-archive](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/11-dashboard-report-archive.md)**: 交付 ReportArchivePage 历史日报归档、飞书卡片仿真渲染、JSON 抽屉与一键重推。
- **[12-scheduled-task-codeup-sync](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/12-scheduled-task-codeup-sync.md)**: 实现 Codeup 定时同步调度任务，1 小时增量重叠窗口与令牌到期通知。
- **[13-scheduled-task-absence-check](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/13-scheduled-task-absence-check.md)**: 实现工作日 18:00 定时缺勤检测任务与补充提交自动撤销。
- **[14-scheduled-task-feishu-report](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/14-scheduled-task-feishu-report.md)**: 实现工作日 09:00 定时日报推送任务与周末/节假日早晨智能跳过。
- **[15-integration-tests](file:///d:/project/02-开源项目/frappe_docker/.scratch/dev-workbench/issues/15-integration-tests.md)**: 交付 6 阶段全链路端到端集成测试与全量自动化回归套件（100% 通过）。

## Fog / Open Questions
- 全部 15 个功能 Issue 已全量解析完成并交付。
