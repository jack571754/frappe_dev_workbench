# 02: App 脚手架和首个页面

**What to build:**

建立 Vue 3 SPA 路由框架、权限鉴权、基础布局和导航，使后续的四个看板 tab 都能复用这个脚手架，快速添加各自的组件和 API。

**Blocked by:** 01

**Status:** resolved

- [x] 创建 app 的 bench route（router.py），映射到一个单页应用入口
- [x] 创建 Vue 3 SPA 主组件和路由定义（使用 vue-router）
- [x] 实现权限检查中间件：只有被标记为"管理者"的飞书用户能访问
- [x] 创建顶部导航栏，包含项目/成员/仓库/豁免四个配置页面的链接
- [x] 创建看板区域，预留四个 tab 的插槽：成员日报、缺勤提醒、项目活跃度、日报归档
- [x] 创建配置页面的菜单入口（Frappe sidebar）
- [x] 实现统计范围切换按钮（全部分支/默认分支），状态保存到 localStorage
- [x] 实现立即刷新按钮，调用后端触发同步的 API
- [x] 在首个 tab（成员日报）放一个空列表框架，验证路由和权限工作正常

## Answer

已完成 Vue 3 SPA 应用脚手架、路由体系、权限鉴权与看板布局构建：

1. **Web 路由与 SPA 托管入口**：
   - 在 `dev_workbench/hooks.py` 中配置 `website_route_rules`，同时支持 `/dev-workbench` 与 `/workbench` 入口路径。
   - 在 `dev_workbench/www/dev_workbench_app.py` 与 `dev_workbench_app.html` 中提供 HTML 单页宿主容器，注入 CSRF Token、Session 数据、用户信息与 Manifest 资源动态解析器。

2. **多层权限安全检查中间件**：
   - **后端中间件**：在 `dev_workbench_app.py` 中拦截 Guest 并重定向至登录页；检查用户是否具备 `Dev Workbench Manager` / `System Manager` / `Administrator` 或关联 `Project Member`（`is_manager=1`），非管理者抛出 `PermissionError` 拒绝访问。
   - **前端导航守卫**：在 `src/router/index.js` 中配置 `router.beforeEach`，非管理者自动跳转至 `/unauthorized` 友好拒绝页面。

3. **Vue 3 SPA 架构与现代设计系统**：
   - **设计系统**：采用定制 Vanilla CSS 设计系统 (`src/style.css`)，引入 Plus Jakarta Sans 字体、玻璃拟态背景 (Glassmorphism)、微动效交互与自适应栅格。
   - **顶部导航栏 (`HeaderNav.vue`)**：
     - 集成品牌 Logo 与标题。
     - 集成项目配置、成员配置、仓库配置、请假豁免等四个配置页面的路由导航链接。
     - 集成分支范围切换器（全部分支 vs 仅默认分支），支持本地持久化并广播事件。
     - 集成「立即刷新」交互按钮，对接后端 `@frappe.whitelist` 接口 `dev_workbench.api.v1.sync.trigger_sync` 并提供动态反馈 Toast。
     - 集成用户头像昵称 Badge 及返回 Desk 按钮。
   - **看板架构 (`DashboardLayout.vue`)**：
     - 预留并渲染四个核心看板 Tab：`成员日报`、`缺勤提醒`、`项目活跃度`、`日报归档`。
   - **首个页面 (`DailyActivityPage.vue`)**：
     - 集成今日活跃成员数、变更代码行数、提交次数、待跟进缺勤人数四个指标卡片。
     - 集成日期与项目筛选栏。
     - 提供美观友好的空列表框架与快捷配置入口。

4. **Frappe Desk 侧边栏与工作区联动**：
   - 在 Frappe Desk 「研发工作台」Workspace 中增加了「打开研发工作台看板 (SPA)」快捷方式与卡片链接，便于管理员从 Desk 一键跳转工作台。

5. **全流程自动化测试通过**：
   - 编写并执行了自动化测试套件 `dev_workbench.tests.test_issue_02.run_issue_02_checks`：
     - 前端 Manifest 与静态资源打包验证通过；
     - Guest 访问重定向与非管理者 403 权限拦截验证通过；
     - 管理者访问注入与上下文会话验证通过；
     - 立即刷新同步 API (`trigger_sync`) 权限与调用逻辑验证通过。


