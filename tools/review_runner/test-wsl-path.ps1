param([string]$Distribution = 'Ubuntu-24.04')
$ErrorActionPreference = 'Stop'
$probeName = 'path probe ' + [char]0x4e2d + [char]0x6587 + ' ' + [guid]::NewGuid().ToString('N')
$probePath = Join-Path (Join-Path $PSScriptRoot '.local') $probeName
New-Item -ItemType Directory -Path $probePath | Out-Null
$previousEncoding = [Console]::OutputEncoding
try {
    foreach ($codePage in @(437, 936, 65001)) {
        [Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding($codePage)
        foreach ($scriptName in @('connect-claude.ps1', 'start-review-runner.ps1')) {
            & (Join-Path $PSScriptRoot $scriptName) -Distribution $Distribution -CheckOnly
            if ($LASTEXITCODE -ne 0) { throw "Launcher failed under code page $codePage : $scriptName" }
        }
        & wsl.exe -d $Distribution --cd $probePath --exec test -d .
        if ($LASTEXITCODE -ne 0) { throw "Unicode workdir failed under code page $codePage" }
    }
} finally {
    [Console]::OutputEncoding = $previousEncoding
    Remove-Item -LiteralPath $probePath
}
Write-Output 'PASS: both launchers and Unicode/space workdirs work under code pages 437, 936, 65001.'
