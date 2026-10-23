# Claude Code 只读审查实施记录

日期：2026-10-21。设计与实施计划位于同目录上一级的 specs 和本目录。代码位于独立 Git 仓库 `development/frappe-bench/apps/dev_workbench`。

## 已交付

- 四个审查 DocType：任务、执行 attempt、问题、执行器；已在当前 site 完成迁移。
- 日报的 AI 审查选择入口、审查列表、代码差异/全文、问题确认/忽略、私有备注、线下反馈标记、复制已确认问题和历史报告查看。
- 创建者与系统管理员权限、独立机器认证、原子领取、租约、过期状态展示、取消、手动重试、报告固定及重复上传幂等。
- 本机 WSL 执行器、固定 Git 对象材料读取、敏感配置与超限跳过、Docker 只读隔离、受限 Claude CLI、输出契约、任务中断及清理。
- 首次连接和启动 PowerShell 脚本、运行手册、ADR-0004。机器令牌写入 Git 已忽略的本机配置，不在终端输出。

## 决策及影响

- Ruling: 保留现有嵌套工作区及未提交改动，就地增加功能，不创建缺失当前应用状态的新 worktree，也不自动提交用户已有变更。影响：交付为工作区改动，未创建 PR 或提交。
- Ruling: 固定版本读取选择白名单本机 Git 仓库，不依赖未验证的新 Codeup diff 接口。影响：其他仓库和缺失 SHA 需要先准备本地对象，再添加路径；当前仅自动匹配到 product_sales_planning。
- Ruling: 采用本机 WSL/Docker 提供只读系统边界，不能把提示词或文件只读属性等同于隔离。影响：Windows 原生 CLI 登录状态不能直接用于隔离环境；需要本人首次认证。
- Ruling: 所有已退出任务立即清理快照，包括失败任务；启动后清理超过 24 小时的异常遗留目录。影响：失败诊断依赖报告与固定错误信息，不保留临时源码材料。
- Ruling: 系统管理员可管理执行器及读取审查记录，普通工作台管理者只能读取本人创建的记录。影响：系统管理员属于受信任的审查管理者，成员不会因为是作者获得访问权。

## 验证与审查

- 报告契约：6 个测试通过，包含路径越界、非法严重程度、行号、去重、缺失覆盖和仓库键隔离。
- WSL 执行器：6 个测试通过，包含固定版本不含未提交代码、只读启动参数、预检不采信模型自述、取消/超时终止材料进程、清理失败仍回收子进程。
- Frappe 集成：覆盖机器领取与租约、取消与重试、记录私有性、问题必须先复核、历史保留、重复上传和过期状态展示。
- HTTP 联调：无效机器凭证拒绝、领取、心跳、材料上传和报告上传全部通过；仅使用合成记录，结束后清理。
- 前端生产构建通过，差异行号专项回归通过。构建仍存在原有主包超过 500 kB 的提示，新增页面使用独立懒加载块。
- 浏览器使用独立合成数据服务验证任务列表、详情、确认问题、保存备注和完成复核；真实 site 对未登录浏览器正确跳转登录页，没有创建测试管理员会话。
- 独立只读代码复核提出的三个重要问题（预检证据、准备阶段取消、特殊差异行号）均补充失败回归测试后修复。清理异常导致快照残留的次要问题一并修复并测试；未遗留该复核提出的已知问题。
- Docker 真实合成探针确认材料挂载不可写、宿主用户目录及 Docker socket 未挂载。

## 尚未完成的运行验收

当前隔离环境缺少 Claude 认证，完整预检按设计失败；执行器没有领取真实任务，没有将成员代码发送到模型，也没有真实 AI 审查结果。本人需先运行 `tools/review_runner/connect-claude.ps1` 完成登录，再运行 `start-review-runner.ps1`。完整认证及文件工具行为通过后，才能验证真实单提交端到端审查。

计划 Task 1 的系统隔离与工具契约已验证，模型认证仍待本人操作；Task 2–4 已实现及测试，Task 5–7 的代码与本地部署已完成，真实模型审查验收尚待认证。此状态不能表述为所有验收完成。

## 2026-10-22：改为复用本机第三方模型配置

用户明确本机 Claude Code CLI 连接第三方模型，不使用官方账号。已移除官方 OAuth/登录流程，读取 Windows `~/.claude/settings.json` 的模型地址、凭证与模型映射白名单，配置中仅保存该文件路径。启动脚本自动更新引用；不会导入开发 hooks、MCP、插件或写入权限，不回退到官方模型。

第三方模型实测预检已通过：CLI 成功读取合成文件，任务外读取被拒绝，Docker 材料只读。执行器专项测试 9 项通过，PowerShell 5/7 与多代码页中文路径测试通过。另修复 CLI 流式系统通知的 message 为字符串时的预检解析异常，并补充失败回归测试。

任务 `kuj7h0nisd` 的仓库已在独立审查目录同步所需版本，2 个变更文件可读取；2026-10-22 已成功领取，进入 running。原开发目录未修改。此记录是任务开始执行的证据，报告最终状态以工作台记录为准。


## 2026-10-22 Alibaba OpenCodeReview integration

Default engine: @alibaba-group/open-code-review 1.13.2, pinned in Dockerfile.ocr. Whitelisted local Claude third-party Anthropic settings are reused without official login. Sanitized two-commit Git reconstruction preserves executable modes and line positions without upstream remote or write credentials. Claude attempt history remains accessible.

Verification: 15 runner, 6 report-contract and 7 live Frappe API tests passed; frontend production build passed. Reviewer confirmed executable-mode regression fixed. Synthetic live preflight passed all three checks. Original task kuj7h0nisd successfully uploaded an OCR report: both files reviewed, zero candidate findings, status partial because OCR reported aggregate token-budget exhaustion with a grace round. This must not be presented as a fully clean review.


## 2026-10-22 Full-project scan

Approved bounded design: add full-project scan to existing private review flow. Implemented repository/branch chooser, server-fixed SHA via Codeup, distinct scan deduplication, task mode persistence and claim routing, Git-object-only full-tree materialization, OCR scan invocation and full-file detail display. No source repository writes or external publishing. Generated/hidden/sensitive/binary/oversize files explicitly skipped. Material limits: 500KB/file, 20MB total, 10000 paths. Candidate display limited to200 with explicit partial/truncation notice; complete raw scan report retained up to20MB. Token budget remains unlimited per user instruction; existing timeouts retained.

Verification: 20 runner tests (including full-tree vs dirty working tree, filters and large candidate report), 6 contract tests, live scan synthetic model call returned2 findings; repository/branch API verified against configured Codeup. Frontend production build passed. Independent reviewer found no remaining Important findings. Upstream scan intentionally supplies no per-file manifest: resulting report conservatively marks coverage incomplete.

Global bench migrate synchronized schema but stalled in unrelated orphan-doctype processing; interrupted the owned migrate process cleanly. Targeted reload_doc and clear_cache completed successfully, verified review_mode/branch columns on live site.


## 2026-10-22 Workload and code-review UI refresh

Approved bounded in-chat design: grouped left navigation for workload/code quality/admin; compact topbar, contextual statistics filters, readable workload summary/table, task summaries and quick filters, three-pane review with adjustable issue width and code focus, mobile adaptation. Implemented in frontend only; existing sync event/API and private review workflow retained. Removed duplicated workload sync controls; kept the global sync action. Unsupported branch/scope selectors removed from routes that do not apply them.

Validation: Vite production build passed (existing main-chunk size warning remains); reviewPresentation and codeReviewDiff Node checks passed. Real authenticated Chrome checks at native1920, 1440x900, and390x844 validated loaded data, task quick filters, native scan-dialog focus, mobile navigation, panel resize/focus mode, detail navigation highlight and page overflow. Temporary viewport reset. Read-only reviewer findings fixed, including scope controls on unsupported routes. No review decisions or remote repository writes performed. Actual UI screenshots stored under ignored tools/review_runner/.local/ui-preview.


## 2026-10-22 Markdown review export

Approved bounded design implemented: detail report section offers Markdown export for the selected attempt, with repository/SHA/version/status/time/engine, readable AI findings, code evidence/suggestions, coverage/limitations and verbatim raw output appendix. OCR comments are exported in full even beyond200; legacy Claude falls back to normalized report. Filenames include repo/SHA/attempt, prose is escaped and code fences expand for embedded backticks. Export uses immutable attempt data rather than editable private notes; blocked during report switching/loading and mismatched attempt selection. UTF-8 BOM download, transient anchor and URL cleanup.

Verification: production build passed; Markdown, task presentation, diff Node checks passed, including history status,201 findings, unsafe filenames/prose, large fence counts and legacy/empty reports. Real authenticated UI current+historical export actions exercised with no console errors; historical switch correctly disabled export until loaded. Browser download-event capture did not return a file handle; exact formatter output was separately written and checked against a live10-finding report, including verbatim raw appendix. Local sample and UI screenshot saved in ignored .local/ui-preview. Read-only review found no Important issue.


## 2026-10-22 Project Desk title branding

Diagnosed live Project tab showing duplicate project name: core Frappe form toolbar sets title + docname, and Project title/name are equal. Added app-owned Project refresh title override to project display name + 研发工作台, with new/legacy name fallbacks. Document identity and desk routing preserved. Node VM regression passed for display name, fallback and new Project; Project client-script cache cleared. Live authenticated browser reload confirmed VisionForge视觉工场 - 研发工作台.


## 2026-10-22 仓库路径前置检查

- 原因：创建/重试未检查本机仓库映射，执行端领取任意仓库后才报 missing_repository。
- 新增执行端仓库检查上报及120秒有效期；按已就绪仓库和审查方式领取任务。批量创建、全扫和重试均先验证，失败不新建任务、不清除历史报告。
- 新增仓库设置面板、提交不可选提示、扫描前拦截、失败详情设置入口。PowerShell配置工具验证Git根目录并原子更新映射；轮询和活动心跳热加载，凭证不改变，本机路径不上传。
- 本机补齐 In_App_Purchasing_System_Front 独立只读审查镜像，验证4个提交及父版本材料可读（29/7/1/6个变更文件），保留失败历史后重新排队；已验证首个任务进入running且上传材料成功，其余3个queued。开发服务与新版执行端已恢复运行。
- 验证：15项Frappe审查集成测试、24项执行端测试、6项报告契约测试、4组前端Node回归检查、HTTP机器认证/领取/心跳/材料/报告合成链路、生产构建通过。构建仍有现有bundle体积提示。浏览器验证未配置仓库禁用全扫、设置弹窗和Esc返回、已就绪路径状态及390px无横向溢出。独立审查发现的活动任务中配置热加载问题已修复并加回归测试。
- 截图：apps/dev_workbench/tools/review_runner/.local/ui-preview/repository-tasks-recovered.png 与 repository-preflight-blocked.png（仅本机，不纳入版本库）。
