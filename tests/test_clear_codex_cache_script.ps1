$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "..\scripts\clear-codex-render-cache.ps1"
$content = Get-Content -Raw -LiteralPath $scriptPath

foreach ($requiredText in @("Get-Process -Name ChatGPT", "Codex is still running", "GPUCache", "Code Cache")) {
    if ($content -notmatch [regex]::Escape($requiredText)) {
        throw "Missing required safety or cache handling: $requiredText"
    }
}

Write-Output "PASS: cache cleanup script requires the client to be closed and targets renderer caches."
