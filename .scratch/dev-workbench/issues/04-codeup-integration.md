# 04: Codeup 集成

**What to build:**

实现 Codeup OpenAPI 调用，支持列仓库、列提交、列成员等基础操作，带有错误处理和重试机制。提供手动同步按钮，展示原始提交数据供验证。

**Blocked by:** 02, 03

**Status:** resolved

- [x] 创建 Codeup API 客户端类，封装 OpenAPI 调用（BaseURL、鉴权、分页）
- [x] 实现 ListRepositories 方法：遍历指定 org 的所有代码库
- [x] 实现 ListCommits 方法：按分支、时间范围、分页参数获取提交列表
- [x] 实现 GetCommit 方法：获取单个提交详情（用于补充行数统计）
- [x] 实现 ListMembers 方法：获取 org 成员列表（邮箱、name、status）
- [x] 错误处理：429 限流时实现指数退避重试；其他错误记录并返回用户友好消息
- [x] 实现令牌有效期检查：过期前 7 天飞书提醒管理者
- [x] 创建后端 API `POST /api/sync/trigger`：手动触发一次 Codeup 数据拉取
- [x] 创建后端 API `GET /api/codeup/identities/unclaimed`：获取所有未关联的 Git 身份列表
- [x] 验证：手动点击刷新按钮，能拉取提交数据并在控制台/日志中查看

## Answer

### 核心实现概览
1. **Codeup OpenAPI 客户端 (`dev_workbench/services/codeup_client.py`)**:
   - 封装 `CodeupClient` 类，支持 `x-yunxiao-token` 请求头鉴权与 OpenAPI BaseURL 配置。
   - 实现 `list_repositories`（按 org 分页/全量拉取仓库）、`list_commits`（按分支、时间范围、分页拉取提交）、`get_commit`（获取单个 commit 详情与行数 stats 统计）、`list_members`（获取企业成员）。
   - 错误处理：支持 429 限流指数退避自动重试（带 jitter 与 Retry-After 解析）；统一解析 401/403/404 与网络异常抛出用户友好 `CodeupAPIError`。

2. **访问令牌到期检查与预警 (`dev_workbench/services/token_service.py`)**:
   - `Codeup Repository` DocType 增加 `token_expires_at`、`last_sync_at`、`last_sync_status`、`last_sync_message` 字段。
   - `check_token_expiry` 服务：当令牌不足 7 天到期时标记 `expiring_soon`，逾期时标记 `expired`，向工作台管理者与系统管理员发送预警并记录 Notification Log。

3. **手动同步与身份发现 API (`dev_workbench/api/v1/sync.py`, `dev_workbench/api/sync.py`)**:
   - `trigger_sync` 校验管理者权限，触发 Codeup 提交拉取。
   - 同步时自动识别 commit 作者邮箱，对未关联的身份自动登记至 `Git Identity` 表（初始状态 `待认领`）。
   - 持久化更新仓库同步状态与时间，返回前 20 条原始提交详情预览（包含 stats、is_merge、author 等）供前端及控制台审计验证。

4. **REST 路由中间件 (`dev_workbench/hooks_middleware.py`, `hooks.py`)**:
   - 注册 `before_request` 钩子，将规范要求的 `/api/sync/trigger`、`/api/codeup/identities/unclaimed` 自动映射至 Frappe 白名单处理方法。

5. **前端交互与控制台验证 (`HeaderNav.vue`)**:
   - 点击"立即刷新"按钮触发数据拉取，通过控制台 `console.log` 输出原始提交预览与统计信息，并通过全局事件广播刷新看板。

6. **自动化测试与验证**:
   - 编写 `dev_workbench/tests/test_issue_04.py`，覆盖 OpenAPI 客户端调用、429 指数退避重试、令牌有效期检查、trigger_sync 数据拉取与权限拦截、未认领身份接口与中间件路由。
   - 执行 `bench --site development.localhost execute dev_workbench.tests.test_issue_04.run_issue_04_checks` 验证结果 100% 通过。
