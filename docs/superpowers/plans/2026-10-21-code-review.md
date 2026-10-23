# Claude Code 只读代码审查实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 管理者从成员日报选择提交，在本机调用 Claude Code 初审，在工作台复核并复制线下反馈。

**Architecture:** Frappe 保存任务、租约、报告和复核记录；Windows 执行器主动轮询，准备固定版本快照并启动受限制的 Claude Code 子进程。Vue 复用现有认证客户端展示任务与代码问题。

**Tech Stack:** Frappe/Python、Vue 3、Windows、Claude Code CLI。执行器独立于 Frappe 运行。

**Spec:** `docs/superpowers/specs/2026-10-21-code-review-design.md`

## Global Constraints

- 第一版手动发起，执行器并发数为 1。
- 单个非合并提交分别审查；批量选择生成多个任务。
- 不修改源码，不执行项目脚本，不评论、推送、合并或同步到仓库。
- 代码只读隔离验证通过后才允许真实成员代码审查。
- 提交摘要继续遵守 ADR-0003，代码审查单独记录新的用途决策。
- 保留当前目录已有改动，不整体暂存、回滚或提交它们。应用是独立的嵌套 Git 仓库，根仓库文档与应用变更分开管理。
- 第一版默认轮询 10 秒、心跳 15 秒、租约 90 秒、超时 20 分钟；参数可配置。
- 私有记录默认仅创建者和显式授权审查管理者可见，不能直接复用所有管理者均可见的读取方式。

## Review Focus

1. SHA 在另一个仓库重复出现、同提交多分支出现：按仓库和完整版本去重。
2. 执行器超时后上传旧报告：过期租约不能覆盖新 attempt 或取消状态。
3. AI 输出越界路径、删除行、非法行号、空报告：验证位置，区分失败、部分覆盖与无发现。
4. 仓库内指令、符号链接、路径穿越：不能扩大工具能力或任务文件访问范围。
5. 普通成员及其他管理者猜测任务 ID：任务、代码、原文、复核 API 均执行同一可见性规则。

## 文件约定

以下 `APP/` 指 `development/frappe-bench/apps/dev_workbench/`。新增实现文件归属于嵌套应用仓库；设计、计划及 ADR 在根仓库。

## Task 1：验证本机 Claude Code 执行边界

**Files:** 新增 `APP/tools/review_runner/preflight.py`、`APP/tools/review_runner/test_preflight.py`、`APP/tools/review_runner/README.md`。

**Interfaces:** `preflight(config) -> {ready: bool, checks: list}`；后续执行器只在 `ready=True` 时领取任务。配置包含工作台 URL、机器凭证引用、快照根目录、CLI 路径和超时。

- [ ] 先编写验证测试：未验证隔离时不允许启动；任务外读取、源码写入、仓库脚本执行均被拒绝；配置和日志不能包含机器令牌。
- [ ] 运行 `python -m unittest discover -s tools/review_runner -p 'test_*.py' -v`，确认先失败于缺少实现。
- [ ] 使用合成仓库验证 CLI 的 `--print`、结构化输出、工具集合 Read/Glob/Grep、restricted、安全模式及不持久化会话。禁止 bypassPermissions、MCP、插件和项目钩子。
- [ ] 验证 Windows 操作系统层面的目录边界；测试快照外诱饵文件不可读取。不得把同一 Windows 用户的文件只读属性误当作完整隔离。当前认证无法与隔离兼容时记录失败，不领取真实任务。
- [ ] 检查真实认证方式是否支持上述 CLI 参数组合和预算选项。认证只读检查或合成模型探针，不发真实源码；不打印认证信息。
- [ ] 测试通过后记录 CLI 版本、支持参数、认证结果和隔离证据。失败时先调整运行方式，再进入真实试用。

## Task 2：定义报告、状态与权限契约

**Files:** 新增 `APP/dev_workbench/services/review_contract.py`、`APP/dev_workbench/tests/test_review_contract.py`、根目录 `docs/adr/0004-read-only-code-review.md`。

**Interfaces:** `validate_report(report, manifest) -> dict`；`review_key(repository, base_sha, head_sha, rules_version, config_version) -> str`；JSON Schema 含 `schema_version/summary/findings/coverage/limitations`。

- [ ] 添加路径穿越、Windows 绝对路径、非法严重程度、未定位发现、old/new 行号、重复路径及不完整覆盖测试。例如 `validate_report(report_with_path('../secret'), manifest)` 必须拒绝。
- [ ] 运行契约测试，确认失败后实现纯 Python 校验，不依赖 Frappe 数据库；位置无法确认时保留为未定位问题。
- [ ] 将执行状态和复核状态分开定义；空发现不自动标记人工已复核。
- [ ] 在 ADR 记录用户授权的代码审查用途，保持提交摘要不发送代码的约束。
- [ ] 重跑契约测试，覆盖 Review Focus 1、3、4。

## Task 3：持久化任务、执行器与复核记录

**Files:** 新增 `APP/dev_workbench/dev_workbench/doctype/code_review_task/`、`code_review_attempt/`、`code_review_finding/`、`code_review_executor/` 下对应 JSON、Python 和初始化文件；新增 `APP/dev_workbench/services/review_service.py`、`APP/dev_workbench/tests/test_review_service.py`。

**Interfaces:** `create_task(activity_log, sha) -> task`；`get_task(name) -> dict`；`review_finding(name, decision, note) -> dict`；`complete_review(task_name) -> dict`。

- [ ] 先写集成测试：未授权读取失败；其他普通管理者不能读取创建者私有任务；重复创建返回同一任务；新 attempt 不覆盖原复核记录。
- [ ] 用当前 site 的 bench 测试命令运行，先观察失败，再添加 DocType 与服务。
- [ ] 服务端从 Daily Activity Log 验证成员、项目、仓库和完整 SHA，不接受前端自行声明的身份或远端 URL。未归属提交提示先认领。
- [ ] 创建者与显式授权审查管理者具有业务读取权限；DocType 不向普通角色开放通用读取原始报告的权限。复核字段由管理者 API 独立更新，机器端不能设置。
- [ ] 执行器凭证只保存安全摘要或 Frappe 支持的受保护凭证，支持撤销；不借用管理者 API key。
- [ ] 执行 `bench --site development.localhost migrate` 后重跑专项测试，验证字段和索引。迁移命令在实际 bench 环境中执行，不假设 Windows 能直接运行容器命令。

## Task 4：任务队列与安全 API

**Files:** 新增 `APP/dev_workbench/api/v1/code_review.py`、`APP/dev_workbench/services/review_queue.py`、`APP/dev_workbench/tests/test_review_queue.py`。

**Interfaces:** 管理 API：`create_tasks/list_tasks/get_task/update_finding/complete_review/cancel_task/retry_task`；执行器 API：`claim_task/heartbeat/upload_report/fail_attempt`。所有写接口 POST，读取 GET。

- [ ] 先测试并发领取只有一个成功、租约过期拒绝报告、取消拒绝迟到结果、重复上传幂等、机器端不能读取未分配任务。
- [ ] 原子领取使用数据库行锁或条件更新；生成随机 lease token，校验执行器、任务、attempt、token 与过期时间。
- [ ] 执行器认证封装为独立校验函数；即使通过 guest 路由进入也必须先完成机器认证，不允许退化为匿名执行。
- [ ] 首版过期任务转为已中断，人工重试创建新 attempt；失败原因限制长度并剔除凭证。
- [ ] 重跑任务、权限和队列测试，覆盖 Review Focus 2、5。

## Task 5：固定版本材料准备与本机执行

**Files:** 新增 `APP/tools/review_runner/runner.py`、`client.py`、`snapshot.py`、`claude.py`、`test_runner.py`；服务器侧新增 `APP/dev_workbench/services/review_materials.py` 及专项测试。

**Interfaces:** `prepare_materials(task) -> {manifest, diff, files, coverage}`；`run_review(materials, config) -> report`；执行器在独立目录运行，不操作开发工作树。

- [ ] 先测试 merge/root commit、删除与重命名、二进制、超大文件、符号链接、失效 SHA、超时和取消；缺失材料不能输出完整审查。
- [ ] 核实 Codeup 提交差异及版本文件读取能力，优先扩展现有服务端只读客户端；若不满足完整材料获取，改用明确白名单的本机只读 Git 镜像，并在实施记录写明选择依据。只交付一种方式。
- [ ] 模型子进程不继承工作台或 Codeup 凭证；网络连接与代码获取由受信任执行器承担，Claude 只看到校验后的材料。
- [ ] 使用参数数组及 stdin 启动子进程，不拼接 shell；采用独立进程组和超时，取消时终止对应进程树。队列进度通过心跳上报。
- [ ] 输出按 Task 2 契约验证，保存受限原文；解析失败不输出无问题。快照清理校验绝对路径属于专用根目录。
- [ ] 用合成材料跑完整领取、审查、上传流程；真实任务仅在 Task 1 所有门槛通过后启用。

## Task 6：工作台页面与日报入口

**Files:** 新增 `APP/frontend/src/pages/CodeReviewPage.vue`、`CodeReviewDetailPage.vue`、`components/CodeReviewCreateDialog.vue`；修改 `components/DashboardLayout.vue`、`pages/DailyActivityPage.vue`、`router/index.js`。

**Interfaces:** 使用现有 `request` API 客户端和 CSRF 处理；任务详情只消费 Task 4 定义的输出。

- [ ] 添加路由、任务列表筛选、批量选择及问题复核的交互验证场景；对 API 失败保留输入并展示原因，避免重复点击创建。
- [ ] 在成员日报行增加入口，选择完整提交列表后创建任务；不将前端展示标题当作仓库唯一标识。
- [ ] 详情采用文件列表、带 old/new 行号的文本差异、问题面板；不使用 `v-html` 渲染源码或报告。未定位问题显示明确说明。
- [ ] 提供确认、忽略、私有备注、人工完成、已线下反馈和复制已确认问题；没有确认问题时说明复制内容为空。
- [ ] 列表区分等待上线、中断、部分完成、执行失败与人工已复核；刷新停止于组件卸载，避免并发覆盖旧页面数据。
- [ ] 运行 `npm run build`，在浏览器验证桌面及窄屏、登录与无权限状态、空态、错误态和完整复核流程。

## Task 7：部署、清理与整体验收

**Files:** 完善 `APP/tools/review_runner/README.md`，新增受控启动脚本和配置示例；实施记录放在本计划同目录的 `2026-10-21-code-review-execution.md`。

**Interfaces:** 执行器前台诊断模式及隐藏启动模式；启动只运行单实例，退出后可恢复轮询。

- [ ] 配置示例不含真实凭证；配置本机启动步骤、认证诊断、暂停、停止与撤销方法。不开启未授权的开机自启。
- [ ] 实现成功快照清理、失败快照 24 小时清理、报告和备注默认 90 天保留及可配置期限；测试清理不能跨专用根目录。
- [ ] 运行全部新增后端测试、执行器测试、前端构建，再验证现有提交摘要和日报专项功能。
- [ ] 在合成仓库证明仓库 hash、工作树和远端状态未改变，再用用户选定的单个真实提交试运行；不得以真实审查替代隔离验证。
- [ ] 检查差异不包含凭证或已有无关变更。汇报实际通过的测试、仍未通过的运行条件和启动方式，不把页面已构建表述为真实审查已可用。

## 计划审查记录

- 已对照设计覆盖任务、租约、私有复核、部分覆盖、只读边界、代码快照、保留期限与前端入口。
- 本计划优先验证隔离与认证；没有通过时不能继续真实代码试运行，但可完成不依赖模型的契约、队列和页面工作。
- 当前不修改业务代码；用户审阅实施计划并确认执行方式后进入实现。建议在当前会话由同一执行者逐项实施，避免多执行者同时修改已有未提交页面。
