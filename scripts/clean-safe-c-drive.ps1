[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$DeveloperCaches
)

$ErrorActionPreference = "Continue"
$beforeFreeBytes = (Get-PSDrive C).Free
$cutoff = (Get-Date).AddDays(-2)
$removedTargets = 0

function Remove-OldTemporaryContent {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $items = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff })
    foreach ($item in $items) {
        if ($PSCmdlet.ShouldProcess($item.FullName, "Remove temporary content")) {
            Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $script:removedTargets++
        }
    }
}

Remove-OldTemporaryContent -Path $env:TEMP
Remove-OldTemporaryContent -Path (Join-Path $env:WINDIR "Temp")

$d3dCache = Join-Path $env:LOCALAPPDATA "D3DSCache"
if (Test-Path -LiteralPath $d3dCache) {
    Get-ChildItem -LiteralPath $d3dCache -Force -ErrorAction SilentlyContinue | ForEach-Object {
        if ($PSCmdlet.ShouldProcess($_.FullName, "Remove Direct3D shader cache")) {
            Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $removedTargets++
        }
    }
}

if ($DeveloperCaches) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        npm cache clean --force
    }
    if (Get-Command pnpm -ErrorAction SilentlyContinue) {
        pnpm store prune
    }
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv cache prune
    }
}

$afterFreeBytes = (Get-PSDrive C).Free
Write-Output "Processed $removedTargets temporary cache entries."
Write-Output ("Recovered {0:N2} GB on C:." -f (($afterFreeBytes - $beforeFreeBytes) / 1GB))
