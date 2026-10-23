param(
    [Parameter(Mandatory=$true)][string]$Repository,
    [Parameter(Mandatory=$true)][string]$Path,
    [string]$Distribution = 'Ubuntu-24.04'
)
$ErrorActionPreference = 'Stop'
& wsl.exe -d $Distribution --cd $PSScriptRoot --exec python3 ./repositories.py --repository $Repository --path $Path
if ($LASTEXITCODE -ne 0) { throw '仓库配置失败，请检查目录后重试。' }
