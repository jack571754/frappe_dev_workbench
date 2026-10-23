param([string]$Distribution = 'Ubuntu-24.04', [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
# Config lives in the data root (%LOCALAPPDATA%\DevWorkbench); legacy .local is migrated on first run.
if ($CheckOnly) {
    & wsl.exe -d $Distribution --cd $PSScriptRoot --exec python3 -c 'from paths import data_root, config_path; print(data_root()); print(config_path())'
} else {
    & (Join-Path $PSScriptRoot 'connect-claude.ps1') -Distribution $Distribution
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & wsl.exe -d $Distribution --cd $PSScriptRoot --exec python3 ./runner.py
}
exit $LASTEXITCODE
