# 10: 看板 - 缺勤和活跃度视图

**What to build:**

实现看板的"缺勤提醒"和"项目活跃度"tab，分别展示缺勤成员列表和 12 周的提交趋势折线图。

**Blocked by:** 05, 06, 07, 08

**Status:** resolved

- [x] 创建缺勤提醒 Vue 组件：
  - 表格展示：成员名、最后提交日期、缺勤天数、豁免状态
  - 支持项目筛选
  - 支持手动标记豁免（打开 AbsenceExemption 编辑页面）
- [x] 创建项目活跃度 Vue 组件：
  - 折线图展示过去 12 周的提交数趋势（每周一条线）
  - x 轴显示周期（周一日期），y 轴显示提交数
  - 支持按项目筛选（显示多个项目的对比）
  - 支持按成员筛选（显示个人的 12 周趋势）
- [x] 调用后端 API `GET /api/absence/list/<date>`：获取缺勤列表
- [x] 调用后端 API `GET /api/activity/project/<project_id>/trend`：获取项目趋势数据
- [x] 实现统计范围切换逻辑：影响趋势图的数据（全部分支 vs 默认分支）
- [x] 验证：缺勤列表能正确显示，趋势图能展示数据，豁免标记生效

## Answer

### 1. 架构与前端视图实现

- **缺勤提醒视图 (`frontend/src/pages/AbsenceActivityPage.vue`)**:
  - **顶部指标看板**：展示【待跟进缺勤成员】（红牌报警）、【已请假豁免成员】（蓝牌）、【缺勤预警总记录】与【连续 2 工作日核查规则】；
  - **筛选与快捷控制**：支持按核查日期（今天/昨天）、所属项目筛选、豁免状态（全部/仅待跟进/仅已豁免）快速过滤；支持一键“重新核查缺勤”；
  - **数据表格**：清晰展示成员姓名（含头像、邮箱）、无提交工作日天数、豁免状态（🔴 待跟进 / 🔵 已请假豁免）、豁免原因/备注说明、最近一次提交日期；
  - **快速标记请假豁免弹窗 (Modal)**：管理者可在缺勤列表针对“待跟进”人员点击【标记请假豁免】，弹窗选择起止日期并填写事由，调用 `POST /api/exemption/grant` 接口持久化并立即重算流转状态。
- **项目活跃度趋势视图 (`frontend/src/pages/ProjectTrendPage.vue`)**:
  - **12 周效能指标概览**：【过去 12 周累计提交】、【周均代码提交产出】、【近 3 周提交总量】与【研发活跃动能 (持续加速/放缓/平稳)】；
  - **交互式折线图 (SVG 响应式渲染)**：
    - X 轴标注每周一所在日期（北京时间，如 `W42 (10/19)`），Y 轴自适应网格对齐；
    - 支持多项目横向对比或单项目下成员细分对比；
    - 曲线悬停支持 Tooltip 展示对象名称、具体周次、提交次数或变更代码行数；
  - **多维过滤**：支持对标项目选择（全部项目横向对比 vs 具体项目）、个人聚焦筛选、统计指标切换（提交次数 vs 变更行数）；
  - **分支范围联动**：全部分支（All Branches）与仅默认分支（Default Branch）无缝切换与重算。

### 2. 后端 API 与服务引擎

- **12 周趋势计算引擎 (`dev_workbench/services/trend_service.py`)**:
  - `get_12_week_trend`：精准计算过去 12 个自然周（周一至周日）区间；
  - 聚合各项目/各成员在指定分支范围下的周提交数、代码行数与活跃人数，计算近期趋势动能；
  - 暴露端点：`GET /api/activity/project/<project_id>/trend`。
- **缺勤与快速豁免服务 (`dev_workbench/api/v1/absence.py`)**:
  - `GET /api/absence/list/<date>?project=...&include_exempted=...`；
  - `POST /api/exemption/grant`：快速创建 `Absence Exemption` 并触发重算；
  - 中间件 `hooks_middleware.py` 转发路由并执行严格管理者权限拦截（403）。

### 3. 构建与自动化测试验证

- 前端产物通过 Vite 成功构建至 `dev_workbench/public/workbench/`，无任何语法及模块异常。
- 自动化测试套件位于 `dev_workbench/tests/test_issue_10.py`。
- 测试覆盖：
  1. 缺勤列表查询、项目过滤与快速标记豁免后的实时状态流转；
  2. 12 周项目活跃度趋势计算（周期划分、全部分支 vs 默认分支数据隔离、项目及成员筛选）；
  3. 非管理者权限拦截验证（403 PermissionError）；
  4. REST 路由中间件转发映射。
- 执行 `bench --site development.localhost execute dev_workbench.tests.test_issue_10.run_issue_10_checks`，100% 验证通过！


