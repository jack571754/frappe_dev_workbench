[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ReportPath = (Join-Path $PWD "codex-performance-report.json"),
    [switch]$CloseChatGPT,
    [switch]$ShutdownWSL
)

$ErrorActionPreference = "Stop"

function Get-ProcessGroups {
    Get-Process -ErrorAction SilentlyContinue |
        Group-Object ProcessName |
        ForEach-Object {
            [pscustomobject]@{
                name      = $_.Name
                count     = $_.Count
                ramMB     = [math]::Round((($_.Group | Measure-Object WorkingSet64 -Sum).Sum) / 1MB)
                privateMB = [math]::Round((($_.Group | Measure-Object PrivateMemorySize64 -Sum).Sum) / 1MB)
            }
        } |
        Sort-Object ramMB -Descending |
        Select-Object -First 20
}

function Test-OpenAIConnection {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        $request = [Net.HttpWebRequest]::Create("https://api.openai.com/v1/models")
        $request.Method = "GET"
        $request.Timeout = 10000
        $request.ReadWriteTimeout = 10000
        try {
            $response = $request.GetResponse()
            $statusCode = [int]$response.StatusCode
            $response.Close()
        }
        catch [Net.WebException] {
            if ($null -ne $_.Exception.Response) {
                $statusCode = [int]$_.Exception.Response.StatusCode
                $_.Exception.Response.Close()
            }
            else {
                throw
            }
        }
        $watch.Stop()
        [pscustomobject]@{ success = $true; statusCode = $statusCode; elapsedMs = $watch.ElapsedMilliseconds; error = $null }
    }
    catch {
        $watch.Stop()
        [pscustomobject]@{ success = $false; statusCode = $null; elapsedMs = $watch.ElapsedMilliseconds; error = $_.Exception.Message }
    }
}

$operatingSystem = Get-CimInstance Win32_OperatingSystem
$memoryCounter = Get-Counter "\Memory\Pages/sec" -SampleInterval 1 -MaxSamples 2
$pagesPerSecond = ($memoryCounter.CounterSamples | Measure-Object CookedValue -Average).Average
$processGroups = @(Get-ProcessGroups)
$actions = [Collections.Generic.List[string]]::new()

if ($CloseChatGPT) {
    $chatGPTProcesses = @(Get-Process -Name ChatGPT -ErrorAction SilentlyContinue)
    if ($chatGPTProcesses.Count -eq 0) {
        $actions.Add("ChatGPT was not running.")
    }
    elseif ($PSCmdlet.ShouldProcess("$($chatGPTProcesses.Count) ChatGPT processes", "Stop independent ChatGPT app")) {
        $chatGPTProcesses | Stop-Process -ErrorAction Stop
        $actions.Add("Stopped $($chatGPTProcesses.Count) ChatGPT processes. Codex was not stopped.")
    }
}

if ($ShutdownWSL) {
    if ($PSCmdlet.ShouldProcess("all WSL distributions", "Run wsl.exe --shutdown")) {
        & wsl.exe --shutdown
        if ($LASTEXITCODE -ne 0) {
            throw "wsl.exe --shutdown failed with exit code $LASTEXITCODE."
        }
        $actions.Add("Shut down WSL to reclaim memory.")
    }
}

$dnsAddresses = @(
    Resolve-DnsName api.openai.com -Type A -ErrorAction SilentlyContinue |
        Where-Object IPAddress |
        Select-Object -ExpandProperty IPAddress
)
$usesFakeIp = @($dnsAddresses | Where-Object { $_ -match '^198\.18\.' -or $_ -match '^198\.19\.' }).Count -gt 0
$network = Test-OpenAIConnection

$totalMemoryMB = [math]::Round($operatingSystem.TotalVisibleMemorySize / 1KB)
$freeMemoryMB = [math]::Round($operatingSystem.FreePhysicalMemory / 1KB)
$memoryUsedPercent = [math]::Round((1 - ($freeMemoryMB / $totalMemoryMB)) * 100, 1)
$recommendations = [Collections.Generic.List[string]]::new()

if ($freeMemoryMB -lt 3072 -or $pagesPerSecond -gt 100) {
    $recommendations.Add("Memory pressure is high. Close unused apps; use -CloseChatGPT for the separate ChatGPT app and -ShutdownWSL only after saving container/WSL work.")
}
if ($usesFakeIp) {
    $recommendations.Add("api.openai.com resolves to the Mihomo Fake-IP range. In Mihomo, test another node and add api.openai.com/openai.com to the appropriate proxy rule; restart Mihomo after changing its configuration.")
}
if (-not $network.success) {
    $recommendations.Add("The OpenAI HTTPS handshake failed. Check Mihomo logs/rules and temporarily compare with Mihomo TUN disabled to isolate the proxy path.")
}
if ($recommendations.Count -eq 0) {
    $recommendations.Add("No strong local bottleneck was detected during this sample. Re-run while the lag is happening.")
}

$report = [ordered]@{
    timestamp        = (Get-Date).ToString("o")
    memory           = [ordered]@{
        totalMB          = $totalMemoryMB
        freeMB           = $freeMemoryMB
        usedPercent      = $memoryUsedPercent
        pagesPerSecond   = [math]::Round($pagesPerSecond, 1)
    }
    processGroups     = $processGroups
    network           = [ordered]@{
        apiHost       = "api.openai.com"
        resolvedIPv4  = $dnsAddresses
        mihomoFakeIp  = $usesFakeIp
        httpsSuccess  = $network.success
        statusCode    = $network.statusCode
        elapsedMs     = $network.elapsedMs
        error         = $network.error
    }
    recommendations  = @($recommendations)
    actionsPerformed = @($actions)
}

$reportDirectory = Split-Path -Parent $ReportPath
if ($reportDirectory -and -not (Test-Path -LiteralPath $reportDirectory)) {
    New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Output "Codex performance report: $ReportPath"
Write-Output "Memory: $memoryUsedPercent% used, ${freeMemoryMB} MB free, $([math]::Round($pagesPerSecond, 1)) pages/sec"
Write-Output "OpenAI HTTPS: success=$($network.success), elapsed=$($network.elapsedMs) ms, MihomoFakeIP=$usesFakeIp"
foreach ($recommendation in $recommendations) {
    Write-Output "Recommendation: $recommendation"
}
foreach ($action in $actions) {
    Write-Output "Action: $action"
}
