#requires -Version 5.1
<#
.SYNOPSIS
  在项目内直接使用 OpenCodeReview（阿里 open-code-review / ocr）做代码审查。

.DESCRIPTION
  一条命令完成：检测 → 按需安装 → 对齐本机 Claude 第三方模型配置 → 项目内绑定 → 执行审查。
  不再把框架源码整份克隆进工程；版本固定在 ocr.version，运行时按需从 npm 拉取。

  默认行为（无参数）：在当前 Git 仓库执行 workspace 模式审查。
  缺少 ocr 时自动安装；缺少 OCR 配置时自动从 %USERPROFILE%\.claude\settings.json 生成，
  不会改动 Claude 自身的配置，也不会把令牌写进工程目录。

.EXAMPLE
  .\ocr.ps1
  在当前仓库审查未提交/已暂存改动。

.EXAMPLE
  .\ocr.ps1 -Check
  只体检：ocr 版本、模型配置、项目绑定状态，不产生任何修改。

.EXAMPLE
  .\ocr.ps1 -Setup
  首次安装全流程：安装 ocr + 写模型配置 + 连通性测试 + 项目内绑定。

.EXAMPLE
  .\ocr.ps1 -Commit abc123 -Background "修复支付回调重复入账"
  审查单个提交，并给出业务背景提升审查质量。

.EXAMPLE
  .\ocr.ps1 -From main -To feature/pay
  审查分支区间。

.EXAMPLE
  .\ocr.ps1 -Scan -Repo D:\code\my-repo
  对指定仓库做全项目扫描。

.NOTES
  固定版本见同目录 ocr.version；与 Docker 执行端镜像版本保持一致。
#>
param(
    [switch]$Check,
    [switch]$Setup,
    [switch]$Install,
    [switch]$Configure,
    [switch]$Bind,
    [switch]$Test,
    [switch]$Preview,
    [switch]$Scan,
    [string]$Commit,
    [string]$From,
    [string]$To,
    [string]$Repo,
    [string]$Background,
    [string]$Language = '中文'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$script:Package = '@alibaba-group/open-code-review'
$script:Version = '1.13.2'
$versionFile = Join-Path $PSScriptRoot 'ocr.version'
if (Test-Path -LiteralPath $versionFile) {
    $pinned = (Get-Content -LiteralPath $versionFile -Raw -Encoding ASCII).Trim()
    if ($pinned) { $script:Version = $pinned }
}
$script:SettingsFile = Join-Path $env:USERPROFILE '.claude\settings.json'
$script:ConfigDir = Join-Path $env:USERPROFILE '.opencodereview'
$script:ConfigFile = Join-Path $script:ConfigDir 'config.json'

# ---------- 输出 ----------
function Write-Step([string]$Message) { Write-Host ('  -> ' + $Message) -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host ('  OK ' + $Message) -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host ('  !  ' + $Message) -ForegroundColor Yellow }
function Write-Fail([string]$Message) { Write-Host ('  X  ' + $Message) -ForegroundColor Red }

# ---------- 基础工具 ----------
function Write-TextFile([string]$Path, [string]$Text) {
    # 统一写 UTF-8 无 BOM：Go/Node 的 JSON 解析都不接受 BOM。
    try {
        $encoding = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($Path, $Text, $encoding)
    }
    catch {
        if ($PSVersionTable.PSVersion.Major -ge 6) {
            Set-Content -LiteralPath $Path -Value $Text -Encoding utf8NoBOM -NoNewline
        }
        else {
            Set-Content -LiteralPath $Path -Value $Text -Encoding UTF8
        }
    }
}

function Read-JsonFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return [pscustomobject]@{} }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if (-not $raw -or -not $raw.Trim()) { return [pscustomobject]@{} }
    return ($raw | ConvertFrom-Json)
}

function Set-JsonProperty($Object, [string]$Name, $Value) {
    if ($Object.PSObject.Properties[$Name]) { $Object.$Name = $Value }
    else { $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value }
}

# 运行外部命令：临时把控制台切到 UTF-8，子进程输出的中文才不会被 OEM 代码页解码成乱码；
# 结束后恢复原编码，不影响调用方会话。
function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    $previous = $null
    try {
        $previous = [Console]::OutputEncoding
        [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    }
    catch { $previous = $null }
    try {
        & $Exe @Arguments | Out-Host
        return $LASTEXITCODE
    }
    finally {
        if ($null -ne $previous) { try { [Console]::OutputEncoding = $previous } catch { } }
    }
}

function Get-RepoRoot([string]$Path) {
    if ($Path) {
        if (-not (Test-Path -LiteralPath $Path)) { throw "仓库目录不存在：$Path" }
        return (Resolve-Path -LiteralPath $Path).Path.TrimEnd('\', '/')
    }
    # 不用 git 原生命令取 toplevel：Windows PowerShell 5.1 按 OEM 代码页解码子进程输出，
    # 含中文的路径会变乱码。这里直接向上找 .git（普通仓库是目录，worktree/子模块是文件）。
    $dir = Get-Item -LiteralPath (Get-Location).Path
    while ($dir) {
        if (Test-Path -LiteralPath (Join-Path $dir.FullName '.git')) { return $dir.FullName.TrimEnd('\', '/') }
        $dir = $dir.Parent
    }
    return (Get-Location).Path.TrimEnd('\', '/')
}

# ---------- ocr 定位与安装 ----------
function Get-OcrPath {
    foreach ($name in @('ocr.cmd', 'ocr.exe', 'ocr')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -and $command.Source -ne $PSCommandPath) { return $command.Source }
    }
    foreach ($candidate in @(
            (Join-Path $env:APPDATA 'npm\ocr.cmd'),
            (Join-Path $env:LOCALAPPDATA 'Programs\ocr\ocr.exe'))) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

function Get-OcrVersion([string]$OcrPath) {
    if (-not $OcrPath) { return $null }
    try { $output = & $OcrPath version 2>$null | Out-String }
    catch { return $null }
    if ($output -match '(\d+\.\d+\.\d+)') { return $Matches[1] }
    return $null
}

function Get-NpmPath {
    foreach ($name in @('npm.cmd', 'npm')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source) { return $command.Source }
    }
    return $null
}

function Install-Ocr {
    Write-Step "安装 ocr CLI $($script:Version)（$($script:Package)）"
    $npm = Get-NpmPath
    if (-not $npm) {
        Write-Fail '未找到 Node.js / npm，无法自动安装 ocr。'
        Write-Host '     安装 Node.js 18+：https://nodejs.org/' -ForegroundColor Yellow
        Write-Host '     或使用官方安装说明：https://open-codereview.ai/docs/installation/' -ForegroundColor Yellow
        try { Start-Process 'https://open-codereview.ai/docs/installation/' | Out-Null } catch { }
        exit 3
    }
    & $npm install -g "$($script:Package)@$($script:Version)"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail 'npm 安装失败。可改用官方 PowerShell 安装脚本：https://open-codereview.ai/install.ps1'
        exit 4
    }
    Write-Ok "ocr $($script:Version) 安装完成"
}

# ---------- 本机模型配置 ----------
function Get-Provider {
    if (-not (Test-Path -LiteralPath $script:SettingsFile)) {
        throw "未找到本机 Claude 配置：$($script:SettingsFile)（请先配置第三方模型地址与令牌）"
    }
    $data = Read-JsonFile $script:SettingsFile
    $envs = $data.env
    if (-not $envs) { throw "本机 Claude 配置缺少 env 段：$($script:SettingsFile)" }

    $base = ([string]$envs.ANTHROPIC_BASE_URL).Trim()
    $authToken = ([string]$envs.ANTHROPIC_AUTH_TOKEN).Trim()
    $apiKey = ([string]$envs.ANTHROPIC_API_KEY).Trim()
    $model = ([string]$envs.ANTHROPIC_MODEL).Trim()
    if (-not $base) { throw '本机 Claude 配置缺少 ANTHROPIC_BASE_URL' }
    if (-not $authToken -and -not $apiKey) { throw '本机 Claude 配置缺少 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY' }
    if (-not $model) { throw '本机 Claude 配置缺少 ANTHROPIC_MODEL' }

    $model = ($model -replace '\[[^\]]*\]\s*$', '').Trim()
    $aliases = @{ opusplan = 'OPUS'; opus = 'OPUS'; sonnet = 'SONNET'; haiku = 'HAIKU'; fable = 'FABLE' }
    $alias = $aliases[$model.ToLowerInvariant()]
    if ($alias) {
        $keyName = 'ANTHROPIC_DEFAULT_' + $alias + '_MODEL'
        $mapped = [string]$envs.$keyName
        if (-not $mapped) { throw "模型为别名 $model，但本机配置缺少 $keyName 映射" }
        $model = ($mapped -replace '\[[^\]]*\]\s*$', '').Trim()
    }
    if (-not $model) { throw '无法从本机 Claude 配置解析出具体模型名' }

    $base = $base.TrimEnd('/')
    if ($base -notmatch '/v1/messages$') {
        if ($base -match '/v1$') { $base = $base + '/messages' } else { $base = $base + '/v1/messages' }
    }
    $header = 'x-api-key'
    if ($authToken) { $header = 'authorization' }
    $token = $authToken
    if (-not $token) { $token = $apiKey }

    return [pscustomobject]@{ Url = $base; Token = $token; Model = $model; AuthHeader = $header }
}

function Get-SavedProvider {
    if (-not (Test-Path -LiteralPath $script:ConfigFile)) { return $null }
    try {
        $config = Read-JsonFile $script:ConfigFile
        if ($config.PSObject.Properties['provider'] -and $config.provider) { return $null }
        if (-not $config.llm) { return $null }
        return [pscustomobject]@{
            Url = [string]$config.llm.url; Token = [string]$config.llm.auth_token
            Model = [string]$config.llm.model; AuthHeader = [string]$config.llm.auth_header
        }
    }
    catch { return $null }
}

function Test-SameProvider($Left, $Right) {
    if (-not $Left -or -not $Right) { return $false }
    return ($Left.Url -eq $Right.Url) -and ($Left.Token -eq $Right.Token) -and
           ($Left.Model -eq $Right.Model) -and ($Left.AuthHeader -eq $Right.AuthHeader)
}

function Set-OcrConfiguration($Provider) {
    if (-not (Test-Path -LiteralPath $script:ConfigDir)) {
        New-Item -ItemType Directory -Path $script:ConfigDir -Force | Out-Null
    }
    $ocr = Get-OcrPath
    $saved = $false
    if ($ocr) {
        # 优先用 ocr 自己的写配置命令：格式与版本一致，且 UTF-8 无 BOM。
        $previous = $env:OCR_NO_UPDATE
        $env:OCR_NO_UPDATE = '1'
        try {
            & $ocr config unset provider *> $null
            $pairs = [ordered]@{
                'llm.url'         = $Provider.Url
                'llm.model'       = $Provider.Model
                'llm.protocol'    = 'anthropic'
                'llm.auth_header' = $Provider.AuthHeader
                'llm.auth_token'  = $Provider.Token
                'language'        = $Language
            }
            $saved = $true
            foreach ($key in $pairs.Keys) {
                & $ocr config set $key $pairs[$key] *> $null
                if ($LASTEXITCODE -ne 0) { $saved = $false; break }
            }
        }
        finally {
            if ($null -eq $previous) { Remove-Item -LiteralPath 'Env:OCR_NO_UPDATE' -ErrorAction SilentlyContinue }
            else { $env:OCR_NO_UPDATE = $previous }
        }
    }
    if ($saved) {
        Write-Ok "模型配置已写入 $($script:ConfigFile)（$($Provider.Model)）"
        return
    }
    # 兜底：ocr 不可用或命令不支持时，直接按官方 llm 段结构写文件。
    Write-Warn '改用直接写入配置（ocr config set 不可用）'
    $config = Read-JsonFile $script:ConfigFile
    # 顶层 provider 会切换到 provider 模式并忽略 llm 段，这里统一走 llm 段。
    if ($config.PSObject.Properties['provider']) { $config.PSObject.Properties.Remove('provider') }
    $llm = [ordered]@{
        url         = $Provider.Url
        auth_token  = $Provider.Token
        auth_header = $Provider.AuthHeader
        model       = $Provider.Model
        protocol    = 'anthropic'
    }
    Set-JsonProperty $config 'llm' ([pscustomobject]$llm)
    Set-JsonProperty $config 'language' $Language
    Write-TextFile $script:ConfigFile ($config | ConvertTo-Json -Depth 12)
    Write-Ok "模型配置已写入 $($script:ConfigFile)（$($Provider.Model)）"
}

# ---------- 项目内绑定 ----------
function Set-ProjectBinding([string]$Root) {
    $dir = Join-Path $Root '.claude'
    $path = Join-Path $dir 'settings.json'
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $config = Read-JsonFile $path
    if (-not $config.PSObject.Properties['enabledPlugins']) { Set-JsonProperty $config 'enabledPlugins' ([pscustomobject]@{}) }
    if (-not $config.PSObject.Properties['extraKnownMarketplaces']) { Set-JsonProperty $config 'extraKnownMarketplaces' ([pscustomobject]@{}) }
    Set-JsonProperty $config.enabledPlugins 'open-code-review@open-code-review' $true
    Set-JsonProperty $config.extraKnownMarketplaces 'open-code-review' ([pscustomobject]@{
            source = [pscustomobject]@{ source = 'github'; repo = 'alibaba/open-code-review' }
        })
    Write-TextFile $path ($config | ConvertTo-Json -Depth 12)
    Write-Ok "项目已绑定：$path"
    Write-Host '     重启 Claude Code 后可用 /open-code-review:review 与 /open-code-review:delegate-review' -ForegroundColor DarkGray
}

# ---------- 体检 ----------
function Test-Binding([string]$Root) {
    $path = Join-Path (Join-Path $Root '.claude') 'settings.json'
    if (-not (Test-Path -LiteralPath $path)) { return $false }
    try {
        $config = Read-JsonFile $path
        if (-not $config.enabledPlugins) { return $false }
        return [bool]$config.enabledPlugins.'open-code-review@open-code-review'
    }
    catch { return $false }
}

function Show-Status {
    $failed = 0
    Write-Host "OpenCodeReview 体检（固定版本 $($script:Version)）" -ForegroundColor White

    $npm = Get-NpmPath
    if ($npm) { Write-Ok "npm：$npm" } else { Write-Warn 'npm：未找到（无法自动安装 ocr）'; $failed++ }

    $ocr = Get-OcrPath
    if ($ocr) {
        $installed = Get-OcrVersion $ocr
        if ($installed) {
            if ($installed -eq $script:Version) { Write-Ok "ocr：$installed（$ocr）" }
            else { Write-Warn "ocr：$installed，固定版本为 $($script:Version)（$ocr）" }
        }
        else { Write-Warn "ocr：已找到但无法读取版本（$ocr）"; $failed++ }
    }
    else { Write-Warn 'ocr：未安装'; $failed++ }

    try {
        $provider = Get-Provider
        Write-Ok "模型来源：$($script:SettingsFile) → $($provider.Model) / $($provider.Url)"
        Write-Ok '令牌：已读取（不显示、不写入工程目录）'
        $saved = Get-SavedProvider
        if (Test-SameProvider $provider $saved) { Write-Ok "OCR 配置：已同步（$($script:ConfigFile)）" }
        else { Write-Warn "OCR 配置：未同步或缺失（$($script:ConfigFile)），运行 -Configure 修复"; $failed++ }
    }
    catch {
        Write-Warn ("模型配置：" + $_.Exception.Message)
        $failed++
    }

    $root = Get-RepoRoot $Repo
    if (Test-Binding $root) { Write-Ok "项目绑定：$root\.claude\settings.json" }
    else { Write-Warn "项目绑定：未绑定（运行 -Bind 绑定 $root）"; $failed++ }

    if ($failed -eq 0) {
        Write-Host '结论：可以直接用 ocr 审查（无需 Docker / 执行端）。' -ForegroundColor Green
        return 0
    }
    Write-Host "结论：有 $failed 项待处理，运行 .\ocr.ps1 -Setup 自动完成。" -ForegroundColor Yellow
    return 1
}

# ---------- 执行审查 ----------
function Invoke-Review($Provider) {
    $ocr = Get-OcrPath
    $root = Get-RepoRoot $Repo
    $managed = @('OCR_NO_UPDATE', 'OCR_ENABLE_TELEMETRY', 'OCR_LLM_URL', 'OCR_LLM_TOKEN',
        'OCR_LLM_MODEL', 'OCR_LLM_PROTOCOL', 'OCR_LLM_AUTH_HEADER')
    $backup = @{}
    foreach ($name in $managed) {
        $item = Get-Item -LiteralPath ('Env:' + $name) -ErrorAction SilentlyContinue
        $backup[$name] = $item
    }
    try {
        # 固定版本、关闭遥测；模型走本次进程环境，避免依赖全局配置漂移。
        $env:OCR_NO_UPDATE = '1'
        $env:OCR_ENABLE_TELEMETRY = '0'
        $env:OCR_LLM_URL = $Provider.Url
        $env:OCR_LLM_TOKEN = $Provider.Token
        $env:OCR_LLM_MODEL = $Provider.Model
        $env:OCR_LLM_PROTOCOL = 'anthropic'
        $env:OCR_LLM_AUTH_HEADER = $Provider.AuthHeader

        $ocrArgs = @()
        if ($Scan) { $ocrArgs += @('scan', '--audience', 'agent') }
        else { $ocrArgs += @('review', '--audience', 'agent') }
        if ($Commit) { $ocrArgs += @('--commit', $Commit) }
        if ($From) { $ocrArgs += @('--from', $From) }
        if ($To) { $ocrArgs += @('--to', $To) }
        if ($Background) { $ocrArgs += @('--background', $Background) }
        if ($Preview) { $ocrArgs += @('--preview') }

        Write-Step "在 $root 执行 ocr $($ocrArgs -join ' ')"
        Push-Location -LiteralPath $root
        try {
            # 子进程输出直接进控制台，不能进函数输出流，否则会被当成返回值。
            $code = Invoke-Native $ocr $ocrArgs
        }
        finally { Pop-Location }
        return $code
    }
    finally {
        foreach ($name in $managed) {
            if (-not $backup[$name]) { Remove-Item -LiteralPath ('Env:' + $name) -ErrorAction SilentlyContinue }
            else { Set-Item -LiteralPath ('Env:' + $name) -Value $backup[$name].Value -ErrorAction SilentlyContinue }
        }
    }
}

# ---------- 主流程 ----------
$root = Get-RepoRoot $Repo
Write-Host "OpenCodeReview · 项目内使用（固定版本 $($script:Version)）" -ForegroundColor White

if ($Check) { exit (Show-Status) }

$setupOnly = $Setup -or $Install -or $Configure -or $Bind -or $Test
$runReview = -not $setupOnly

if ($Install -or $Setup) {
    if (-not (Get-OcrPath)) { Install-Ocr } else { Write-Ok "ocr 已安装：$(Get-OcrPath)" }
}
if ($Configure -or $Setup -or $Test) {
    $provider = Get-Provider
    Set-OcrConfiguration $provider
    $ocr = Get-OcrPath
    if ($Test -or $Setup) {
        Write-Step '连通性测试：ocr llm test'
        $testCode = Invoke-Native $ocr @('llm', 'test')
        if ($testCode -ne 0) {
            Write-Fail '模型连通性测试失败：检查 ANTHROPIC_BASE_URL / 令牌 / 模型名。'
            exit 6
        }
        Write-Ok '模型连通'
    }
}
if ($Bind) { Set-ProjectBinding $root }

if (-not $runReview) {
    Write-Host '完成。' -ForegroundColor Green
    exit 0
}

# 默认：确保可用后直接审查（首次运行自动补齐安装与配置）
$ocr = Get-OcrPath
if (-not $ocr) {
    Write-Warn '未检测到 ocr，自动安装…'
    Install-Ocr
    $ocr = Get-OcrPath
}
$installed = Get-OcrVersion $ocr
if ($installed -and $installed -ne $script:Version) {
    Write-Warn "本机 ocr 为 $installed，脚本固定版本为 $($script:Version)（继续使用已安装版本）"
}
try { $provider = Get-Provider }
catch {
    Write-Fail $_.Exception.Message
    exit 2
}
if (-not (Test-SameProvider $provider (Get-SavedProvider))) { Set-OcrConfiguration $provider }
exit (Invoke-Review $provider)
