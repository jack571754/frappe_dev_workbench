param(
  [string]$SiteName = "frontend",
  [string]$BackendContainer = "frappe_docker-backend-1",
  [string]$FeishuAppId = $env:FEISHU_APP_ID,
  [string]$FeishuAppSecret = $env:FEISHU_APP_SECRET
)

$ErrorActionPreference = "Stop"

function Invoke-Bench {
  param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$BenchArgs
  )

  & docker exec -w /home/frappe/frappe-bench $BackendContainer bench @BenchArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: bench $($BenchArgs -join ' ')"
  }
}

Write-Host "[1/3] Running migrate for site '$SiteName'..."
Invoke-Bench "--site" $SiteName "migrate"

if ($FeishuAppId -and $FeishuAppSecret) {
  Write-Host "[2/3] Initializing Feishu social login..."
  $pyAppId = $FeishuAppId.Replace("\", "\\").Replace("'", "\'")
  $pyAppSecret = $FeishuAppSecret.Replace("\", "\\").Replace("'", "\'")
  $kwargsPy = "{'app_id':'$pyAppId','app_secret':'$pyAppSecret','enable':True}"

  Invoke-Bench "--site" $SiteName "execute" "product_sales_planning.api.v1.feishu_setup.setup_feishu_login" "--kwargs" $kwargsPy
  Invoke-Bench "--site" $SiteName "execute" "product_sales_planning.api.v1.feishu_setup.check_feishu_config"
} else {
  Write-Host "[2/3] FEISHU_APP_ID/FEISHU_APP_SECRET not set. Skip Feishu setup."
}

Write-Host "[3/3] Clearing cache..."
Invoke-Bench "--site" $SiteName "clear-cache"

Write-Host "Done."
