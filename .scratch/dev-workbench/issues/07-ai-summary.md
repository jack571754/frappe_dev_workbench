# 07: AI 摘要生成

**What to build:**

实现 OpenAI 兼容接口集成，根据提交信息和文件列表生成一句话摘要，不发送代码 diff（安全考虑）。结果缓存到 DailyActivityLog。

**Blocked by:** 04

**Status:** resolved

- [x] 创建 OpenAI 兼容 API 客户端类（支持自定义 base_url、api_key、model_name）
- [x] 实现 Frappe 系统设置页面，配置 AI 模型参数（URL、Key、Model）
- [x] 实现摘要生成 prompt 构造：输入格式为"提交信息列表 + 文件列表"（不含 diff）
- [x] 实现摘要内容要求：单句话，中文，不超过 100 汉字，描述做了什么
- [x] 实现错误处理：API 失败时记录错误，不阻塞整个流程，摘要字段标记为"生成失败"
- [x] 实现摘要缓存：已生成的摘要不重复调用 API
- [x] 实现异步调用：大量摘要生成时不阻塞主流程，使用后台任务或异步调用
- [x] 在 DailyActivityLog 中存储摘要结果
- [x] 验证：能成功调用 API 并生成摘要

## Answer

### 1. 架构与功能实现

- **OpenAI 兼容客户端 (`dev_workbench/services/ai_client.py`)**:
  - `OpenAIClient`：支持任意 OpenAI 兼容服务（OpenAI 官方、阿里云百炼通义千问、DeepSeek、Moonshot、Ollama 等）。
  - 支持配置 `base_url`、`api_key`、`model`、`temperature`、`max_tokens` 及超时控制。
  - 自定义 `AIServiceError` 异常结构，提供明确的错误码与响应跟踪。
- **系统设置模型与页面 (`Dev Workbench Settings`)**:
  - 创建 Single DocType `Dev Workbench Settings`，位于 `dev_workbench/doctype/dev_workbench_settings/`。
  - 包含 AI 配置区块：`ai_enabled`、`ai_base_url`、`ai_api_key` (Password 字段)、`ai_model`、`ai_temperature`、`ai_max_tokens`。
  - Frappe Desk 工作区已自动集成该配置入口；并提供 `GET/POST /api/settings/ai` 接口供工作台或配置中心调用（敏感 API Key 自动脱敏为 `sk-***`）。
- **Prompt 构造与安全策略 (严格遵循 ADR 0003)**:
  - 构造函数 `build_summary_prompt(commits)` 仅提取清洗后的 Commit 标题/说明与变更文件路径列表。
  - 严格杜绝传递代码 diff，保证公司内部源码不流向第三方大模型。
- **摘要规范与清洗过滤**:
  - 设定 Prompt 严格约束单句话、中文、不超过 100 汉字。
  - `clean_and_truncate_summary` 函数自动剔除换行、引号、“今日完成了”等废话前缀，并将超长文本截断至 100 字符以内。
- **容错、缓存与异步机制 (`dev_workbench/services/ai_summary_service.py`)**:
  - **错误隔离**：API 调用超时或失败时不崩溃主流程，记录至 `frappe.log_error`，将 `DailyActivityLog.summary` 标记为 `"生成失败"`。
  - **摘要缓存**：非强制重算且非“生成失败”时，命中缓存直接返回，不发起网络请求。
  - **异步队列**：提供 `enqueue_summary_generation` 及 `generate_daily_summaries_background`，利用 `frappe.enqueue` 支持后台异步任务生成，避免阻塞前台接口。
- **REST 路由与权限中间件 (`hooks_middleware.py`)**:
  - 统一映射 `/api/settings/ai` (GET/POST) 与 `/api/activity/summary/regenerate`、`/api/activity/summary/batch-generate`。
  - 严格校验 `Dev Workbench Manager` / `System Manager` 权限。

### 2. 自动化测试与验证

- 自动化测试用例位于 `dev_workbench/tests/test_issue_07.py`。
- 测试覆盖：
  1. 系统设置存取与 API Key 脱敏展示；
  2. Prompt 构造器安全性（仅 Commit 标题与文件路径，严禁 diff）；
  3. 摘要内容规范（单句话、中文、<=100 汉字、前缀清洗）；
  4. OpenAI API 调用模拟、数据清洗与 `DailyActivityLog.summary` 存储；
  5. 摘要缓存命中机制（已存在摘要时不重复请求 API）；
  6. 错误处理与容错机制（API 异常时打标“生成失败”，记录系统日志且不阻塞流程，支持失败重试）；
  7. 批量生成与异步后台队列任务接口；
  8. REST API 权限控制与路由中间件转发。
- 执行命令 `bench --site development.localhost execute dev_workbench.tests.test_issue_07.run_issue_07_checks`，所有 8 项检查 100% 通过且完全清理测试数据。


