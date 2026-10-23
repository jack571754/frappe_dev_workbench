param([string]$Distribution = 'Ubuntu-24.04', [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
if ($CheckOnly) {
    & wsl.exe -d $Distribution --cd $PSScriptRoot --exec test -f ./local_provider.py
} else {
    $settingsFile = Join-Path $env:USERPROFILE '.claude/settings.json'
    & wsl.exe -d $Distribution --cd $PSScriptRoot --exec python3 ./local_provider.py --settings-file $settingsFile --config ./.local/config.json
}
exit $LASTEXITCODE
