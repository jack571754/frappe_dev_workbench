# OpenCodeReview 本机只读审查执行端

运行位置：当前 Windows 电脑上的 Ubuntu WSL，使用本机 Docker。网页负责排队和复核，默认执行端使用阿里 `alibaba/open-code-review` 官方 CLI（固定已验证的发布版本 1.13.2），不实现新的智能体。复用 Windows 本机 Claude Code CLI 的第三方模型配置，不使用官方账号登录或 OAuth。

## 项目内直接使用（推荐，无需克隆框架）

框架源码不再放进工程（原 `.local/vendors/open-code-review` 已移除，14.5MB）。版本只记录在本目录 `ocr.version`，需要时按需从 npm 安装，并用本机 Claude 的第三方模型配置直接跑。

```powershell
# 在任意仓库目录里执行（默认审查当前仓库，不需要先 cd 到本工具目录）
& 'D:\...\tools\review_runner\ocr.ps1'          # 日常：审查当前仓库改动
& 'D:\...\tools\review_runner\ocr.ps1' -Setup   # 首次：安装 ocr + 写模型配置 + 连通性测试 + 项目内绑定
& 'D:\...\tools\review_runner\ocr.ps1' -Check   # 只体检，不产生任何修改
```

也可以直接 `.\ocr.ps1`（PowerShell）或 `.\ocr.cmd`（cmd/双击），此时审查的是当前目录所在仓库。

- 缺 `ocr` 时自动执行 `npm i -g @alibaba-group/open-code-review@<ocr.version>`；连 npm 都没有时会打开官方安装说明，而不是直接报错退出。
- 模型地址、令牌、模型名取自 `%USERPROFILE%\.claude\settings.json`，按 `opus/sonnet/haiku/fable` 别名解析到 `ANTHROPIC_DEFAULT_*_MODEL` 后写入 `~/.opencodereview/config.json`（`ocr config set`，UTF-8 无 BOM）。不改 Claude 自身配置，不把令牌写进工程目录。
- `-Bind` 在目标仓库的 `.claude/settings.json` 启用 `open-code-review@open-code-review` 插件；重启 Claude Code 后可用 `/open-code-review:review`（采纳修复）和 `/open-code-review:delegate-review`（由宿主模型审查，无需另配 LLM）。
- 其他用法：`-Commit <sha>`、`-From main -To feature`、`-Scan`、`-Preview`（只列出将审查的文件，不调用模型）、`-Repo <path>`、`-Background "需求背景"`、`-Language English`。

这条路径是开发者本机快捷方式：不经过工作台任务队列、不做容器只读隔离、消耗的是本机模型额度。需要隔离、留痕和人工复核时，仍使用下面的 Docker 执行端。

## 数据目录与环境面板（网页一键检查）

执行端的数据都在**数据目录**里，默认 `%LOCALAPPDATA%\DevWorkbench`（WSL 下对应 `/mnt/c/Users/<用户>/AppData/Local/DevWorkbench`），可用环境变量 `DEV_WORKBENCH_HOME` 覆盖。配置、仓库缓存、快照、日志都不再写入项目目录；旧版本的 `tools/review_runner/.local` 会在执行端第一次启动时自动迁移过去，确认无误后可以整个删除。

工作台「代码审查」页的**环境与同步**面板：

- **一键检查**：让在线执行端重新采集 Python / Git / Docker / 审查镜像 / OCR 镜像 / 数据目录 / 执行端配置 / 模型配置，结果回显网页。
- **一键配置**：创建数据目录、迁移旧 `.local`，并把每一步结果回传。
- **数据目录**：可以改成任何绝对路径；执行端在下一轮上报时自动切换，并把配置同时写回新目录，重启后仍生效。

启动执行端：`.\start-review-runner.ps1`；`.\start-review-runner.ps1 -CheckOnly` 只打印当前数据目录与配置文件位置，方便排查。

## 已有的边界

- Docker 源码挂载只读，容器根文件系统只读，非 root、无 capabilities，不挂载 Docker socket、用户目录、工作台凭证或 Codeup 凭证。
- OpenCodeReview 使用内置审查规则和只读工具，在临时的无远端 Git 快照中执行；不加载待审仓库的隐藏指令/工具配置，不向容器提供仓库写入凭证。
- 执行器从白名单本机仓库读取 Git 对象；人工配置的开发目录不会 checkout、fetch、commit 或 push。一键准备创建的专用裸仓库缓存允许只读 fetch，每次审查前自动同步固定 SHA，不包含本地未提交代码，不向远端写入。
- 新旧变更文件和有限的同版本上下文供模型读取，超大、二进制和敏感配置明确跳过。凭证、环境文件和私钥不作为材料发送；这不是任意源码内容的秘密扫描器。
- 代码会发送至本机 Claude Code 配置的第三方模型服务。OpenCodeReview 直接调用该模型，报告和备注仅在工作台保存，确认问题后由管理者线下沟通。
- 工作台保留原始提交 SHA；为避免向模型暴露完整历史、远端地址或凭证，OCR 对经过过滤的新旧代码构建临时提交，行号与对应版本文件一致。超限或未覆盖内容标为部分完成，不把空报告视为无问题。

## 构建与机器配置

在 WSL 的应用目录执行：

```bash
docker build -t dev-workbench-review:2.1.306 tools/review_runner
docker build -t dev-workbench-ocr:1.13.2 -f tools/review_runner/Dockerfile.ocr tools/review_runner
```

执行端镜像的 OCR 版本以 `tools/review_runner/ocr.version` 为准（`Dockerfile.ocr` 的 `OCR_NPM_VERSION` 构建参数），工程内不保留框架源码。

数据库同步和本机凭证初始化在 Frappe 容器执行：

```bash
bench --site development.localhost migrate --skip-search-index
bench --site development.localhost execute dev_workbench.services.review_setup.provision_local
```

初始化会在 `tools/review_runner/.local/config.json` 创建配置，机器令牌只写文件，不打印；文件已加入 Git 排除规则。该便捷初始化专用于当前 Windows D 盘工作区的挂载方式，其他部署自行调整配置。

`repositories` 映射键必须与工作台 Codeup Repository 的 name 完全一致，值为 WSL 可访问的本地 Git 目录。自动登记能匹配的 apps 目录；其他代码库可在网页一键准备，或由管理者添加已有本地仓库。执行器只从工作台登记的 Codeup 仓库下载，不接受任意远端地址。

### 仓库检查与路径设置

代码审查页的「仓库设置」显示每个启用仓库的本机状态；提交选择和全项目扫描也会在创建前检查。未配置、目录不可读或执行端离线时不能创建或重试；批量请求会先检查全部仓库，避免逐个失败。

推荐流程：选择仓库 → **一键准备仓库** → 等待状态变为 **自动同步**。已有手动映射也可以点击 **启用自动同步**，切换到独立缓存；原开发目录不修改。准备任务会显示等待下载、正在下载或失败原因，可关闭弹窗继续使用工作台；不会因为关闭页面中止。执行端正在审查时，准备任务顺序排队，不中断当前审查。

专用缓存位于配置文件同级的 `managed-repositories/<仓库名SHA256>.git`，包含所有权标记，拒绝符号链接或非管理缓存。首次只下载默认分支的有限历史，后续按任务固定的 head/base SHA 同步；不 checkout、不运行仓库脚本、不推送。初次准备最长10分钟，审查阶段的同步计入原任务超时。磁盘与仓库网络访问由当前执行端承担。

复用服务端已配置的 Codeup 凭证，不新增官方登录。只有绑定到指定执行端、未过期的准备/审查租约可读取下载源和凭证。Git 认证仅存在于受控 Git 子进程环境中，不放入命令参数、远端URL、本机配置、数据库报告或模型容器；禁用重定向、全局凭证助手、模板与 hooks，并清理继承的 Git 环境变量。当前仅支持 `https://codeup.aliyun.com` 地址，失败时提示检查凭证、权限、空仓库、网络或磁盘空间。

在当前电脑准备本地 Git 仓库后，在执行器目录的 PowerShell 中运行（替换为真实仓库名、目录）：

```powershell
.\configure-repository.ps1 -Repository 'In_App_Purchasing_System_Front' -Path 'D:\代码目录\前端仓库'
```

支持正常工作区和裸仓库。命令验证 Git 目录后只更新路径映射，保留模型和连接配置，不修改仓库源码或远端。执行端在轮询及审查心跳时热加载映射，通常 10～20 秒后可在网页重新检查。升级前的旧执行端需停止并重新运行 `start-review-runner.ps1` 一次。

工作台只接收仓库名、检查状态及支持的审查方式，不接收本机绝对路径。检查结果 120 秒未刷新后失效；旧执行端仅保持连接不代表支持一键准备。多执行端只领取自己已检查通过的仓库任务，准备任务绑定发起时选择的在线执行端。手动路径检查不等于提交已同步：仅人工配置的目录仍由管理者更新；自动缓存会在审查前同步需要的版本。

## 复用本机第三方模型

Windows PowerShell 在本目录运行：

```powershell
.\start-review-runner.ps1
```

启动脚本会自动读取当前 Windows 用户的 `~/.claude/settings.json`，登记配置文件路径，再启动执行器。`connect-claude.ps1` 现在仅更新配置引用，不再发起官方登录。

只读取模型地址、AUTH_TOKEN/API_KEY、模型名和模型映射白名单，转换为 OpenCodeReview 的 `OCR_LLM_*` 进程环境。opus/sonnet/haiku/fable 等 CLI 别名会解析到配置的实际模型名。不会加载本机的 hooks、插件、MCP 或开发写入权限；不会把模型密钥复制到工作台配置、命令参数或日志。不提供官方模型的静默回退。

执行器每次模型调用都重新读取本机配置；更换第三方模型或密钥后无需重新登录官方账号。配置缺少地址或密钥时预检失败，不领取任务。

## 预检与运行

```bash
python3 tools/review_runner/runner.py --config tools/review_runner/.local/config.json
```

启动时完整预检只用合成 Git 提交验证容器只读、OCR 版本及第三方模型真实审查调用，可能消耗少量模型额度。预检失败不会领取任务。执行器运行期间保持终端打开；Ctrl+C 停止，不默认配置开机启动。

默认 `engine` 为 `open-code-review`。需手动切回旧 CLI 时可在本机配置设为 `claude`；不存在失败后静默回退。实际执行引擎和版本记录在每次审查报告中，历史 Claude 报告继续可读。

同一配置使用文件锁防止重复运行；并发数 1，轮询默认 10 秒，心跳 15 秒，租约 90 秒。提交审查默认总时限 20 分钟（`timeout_seconds`）；全项目扫描独立使用 `scan_timeout_seconds`，默认 `0` 表示不限制总时长，设置正数可限制秒数。无总时限时仍持续心跳、响应取消，模型请求与单文件处理仍受引擎超时保护。可配置 `poll_seconds`；OCR token 总预算不设上限（`--max-tokens-budget 0`），`max_budget_usd` 仅适用于旧 Claude 引擎且需认证方式支持。

## 故障处理和数据保存

- 等待上线：检查执行器是否运行、完整预检是否通过、工作台 URL 与机器令牌是否有效。
- 未配置仓库：在页面「仓库设置」点击一键准备；也可手动运行 `configure-repository.ps1`。配置完成后重试，原失败报告和执行历史继续保留。
- 不支持一键准备：升级后重启执行端一次，正常预检通过后会自动上报支持状态。重复点击只复用当前准备任务，不重复下载。
- 自动同步失败：检查 Codeup 凭证、仓库读取权限、网络与磁盘空间，可在仓库设置中重新准备；不能同步固定版本时不会审查过期版本。
- 已中断：任务租约失效，不自动重复收费；人工重试建立新 attempt，原报告与复核记录保留。
- 解析失败：工作台显示原始模型报告（若有），不会显示为没有问题。
- 取消或停止执行器会终止对应容器；任务目录在退出时清理，包括失败材料，不保留在用户开发目录。
- 管理员可通过 `revoke_executor` API 撤销机器令牌；已撤销凭证不能再领取或上传任务。
- 工作台按 `review_retention_days` 配置清理已结束报告（默认 90 天），不清理活动任务；执行端启动时清理超过 24 小时的遗留 task 目录。

## 验证

```bash
python3 -m unittest discover -s tools/review_runner -p 'test_*.py' -v
python3 -m unittest discover -s dev_workbench/tests -p test_review_contract.py -v
bench --site development.localhost execute dev_workbench.tests.test_review_api.run_checks
bench --site development.localhost execute dev_workbench.tests.test_review_repository_preparation.run_checks
cd frontend && npm run build
```

项目内使用路径自检（Windows PowerShell，不消耗模型额度）：

```powershell
.\tools\review_runner\ocr.ps1 -Check
```


## 全项目扫描

代码审查页点击“全项目扫描”，选择仓库和分支；创建时从 Codeup 确认并固定分支的完整提交 SHA。执行端使用 `ocr scan` 扫描该版本全部可读取文件，不读取本地未提交内容，支持合并提交。自动缓存会同步此 SHA；手动配置目录需事先具有对应提交。历史提交审查与全扫任务分开去重，报告继续私有保存并人工复核。

全扫不限制 token 总预算。敏感/隐藏配置、生成目录、二进制、符号链接和子仓库不发送，单文件超过 500KB 或总材料超过 20MB 的文件逐项标为未覆盖；超过 10000 个文件明确失败。引擎自行排除或未返回覆盖凭据的文件同样标为未覆盖。全扫材料只构造临时无远端快照，不修改原仓库。全扫不再共用提交审查的 20 分钟限制，使用 `scan_timeout_seconds`（默认 `0`，无固定总时限）；单次模型请求使用 `ocr_request_timeout_seconds`（默认 120 秒），单文件并发任务预算为 10 分钟，可随时取消。升级执行器后须重启 PowerShell 启动脚本以加载新逻辑。

当前 OCR 1.13.2 scan 不输出逐文件 manifest，报告会明确注明逐文件覆盖凭据不足并显示部分完成，不能据此承诺全仓无问题。超过200项候选时展示前200项并明确总数，完整结果保留在原始报告（全扫最大20MB）。
