# 03: 配置页面

**What to build:**

建立四个 Frappe Desk 配置页面（使用原生 Form），使管理者能管理项目、成员、仓库、豁免数据。集成飞书通讯录导入成员功能。

**Blocked by:** 02

**Status:** resolved

- [x] ProjectSettings 页面（Frappe Form）：创建、编辑、删除项目；显示项目下的仓库列表
- [x] RepositoryConfig 页面（Frappe Form）：管理仓库信息，配置排除文件规则（glob 列表编辑器）
- [x] MemberSettings 页面（Frappe List + Detail）：
  - [x] 从飞书通讯录导入成员列表（调用飞书 API，存入 ProjectMember）
  - [x] 显示每个成员的 Git 身份列表和关联状态
  - [x] 支持手动添加新 Git 身份
  - [x] 支持认领未归属的 Git 身份
- [x] AbsenceExemption 页面（Frappe Form）：选择成员和日期范围，标记请假豁免
- [x] 所有页面都需要权限检查（仅管理者可见）
- [x] 验证数据能保存到对应的 DocType

## Answer

已完成四个核心配置页面（Frappe Desk Form + Vue SPA 双端）与飞书成员/身份认领管理闭环：

1. **项目配置 (ProjectSettings)**：
   - Desk Form (`project.js`)：支持项目创建、编辑、删除、查看关联代码库列表，提供「打开研发工作台看板」及「添加关联代码库」快捷动作。
   - SPA 视图 (`ProjectSettingsPage.vue`)：动态加载已建项目及代码库统计。

2. **代码仓库配置 (RepositoryConfig)**：
   - Desk Form (`codeup_repository.js`)：管理 Codeup 组织 ID、代码库 ID、访问令牌、默认分支；提供「重置为默认排除规则」一键载入标准 glob 模式以及连通性测试。
   - SPA 视图 (`RepositoryConfigPage.vue`)：直观呈现代码库参数与生效状态。

3. **成员与 Git 身份管理 (MemberSettings)**：
   - 后端管理接口 (`dev_workbench.api.v1.members`)：
     - `import_feishu_contacts`：从飞书通讯录 API 及系统用户中批量同步成员，自动创建并更新 `Project Member`（测试验证成功同步 97 位成员）。
     - `get_unclaimed_identities`：查询待认领的 Git 邮箱/用户名库。
     - `claim_git_identity`：管理者认领指定 Git 身份并双向联动更新成员子表。
     - `add_git_identity`：支持直接为成员手动录入新 Git 邮箱并自动认领。
   - Desk List & Form (`project_member_list.js`, `project_member.js`)：
     - 列表视图集成「从飞书通讯录同步成员」按钮。
     - 详情表单集成「认领未归属 Git 身份」弹窗及「添加新 Git 身份」对话框。
   - SPA 视图 (`MemberSettingsPage.vue`)：集成待认领身份预警横幅、成员搜索、身份归属卡片与认领 Modal。

4. **请假豁免 (AbsenceExemption)**：
   - Desk Form (`absence_exemption.js`)：默认填入当前工作日，并提供前置日期校验（结束日期不可早于开始日期）。
   - SPA 视图 (`AbsenceExemptionPage.vue`)：列表呈现各成员的生效豁免记录。

5. **全流程权限拦截与测试验证**：
   - 所有配置页面和管理接口均校验 `Dev Workbench Manager` 角色，非管理者调用时严格抛出 `PermissionError`。
   - 自动化测试套件 `dev_workbench.tests.test_issue_03.run_issue_03_checks` 执行全部通过（100% 验证通过通讯录导入、身份添加、身份认领及权限拦截）。


