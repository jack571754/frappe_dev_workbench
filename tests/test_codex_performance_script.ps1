$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "..\scripts\codex-performance.ps1"
$reportPath = Join-Path $env:TEMP "codex-performance-test-$PID.json"

try {
    & $scriptPath -ReportPath $reportPath

    if (-not (Test-Path -LiteralPath $reportPath)) {
        throw "The diagnostic report was not created."
    }

    $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
    foreach ($property in @("timestamp", "memory", "processGroups", "network", "recommendations", "actionsPerformed")) {
        if ($null -eq $report.PSObject.Properties[$property]) {
            throw "The report is missing property '$property'."
        }
    }

    if (@($report.actionsPerformed).Count -ne 0) {
        throw "The default diagnostic mode must not perform remediation actions."
    }

    Write-Output "PASS: default mode is diagnostic-only and writes a structured report."
}
finally {
    Remove-Item -LiteralPath $reportPath -Force -ErrorAction SilentlyContinue
}
