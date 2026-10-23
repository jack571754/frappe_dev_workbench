[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = "Stop"

$runningClient = @(Get-Process -Name ChatGPT -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*OpenAI.Codex_*"
})

if ($runningClient.Count -gt 0) {
    Write-Error "Codex is still running. Close the Codex/ChatGPT client manually, then run this script again. No files were changed."
    exit 1
}

$package = Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory |
    Where-Object Name -like "OpenAI.Codex_*" |
    Select-Object -First 1

if ($null -eq $package) {
    throw "The Codex package data directory was not found."
}

$webRoot = Join-Path $package.FullName "LocalCache\Roaming\Codex\web\Codex\codex-browser-app\Default"
$cachePaths = @(
    (Join-Path $webRoot "Cache"),
    (Join-Path $webRoot "Code Cache"),
    (Join-Path $webRoot "GPUCache")
)

$removed = [Collections.Generic.List[string]]::new()
foreach ($cachePath in $cachePaths) {
    if (Test-Path -LiteralPath $cachePath) {
        if ($PSCmdlet.ShouldProcess($cachePath, "Remove renderer cache")) {
            Remove-Item -LiteralPath $cachePath -Recurse -Force
            $removed.Add($cachePath)
        }
    }
}

if ($removed.Count -eq 0) {
    Write-Output "No Codex renderer caches were found to remove."
}
else {
    Write-Output "Removed $($removed.Count) Codex renderer cache directories. Start Codex again."
}
