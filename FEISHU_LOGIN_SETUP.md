# Feishu Login Setup (product_sales_planning)

## 1. Root Cause
Current site `frontend` does not have `Social Login Key` named `feishu`, so the Feishu login option is not rendered.

Checked result:

```bash
bench --site frontend execute product_sales_planning.api.v1.feishu_setup.check_feishu_config
# output: ❌ 飞书登录未配置
```

## 2. Fix (Recommended)
Run inside backend container:

```bash
docker exec -it frappe_docker-backend-1 bash
cd /home/frappe/frappe-bench
bench --site frontend console
```

In `bench console`, execute:

```python
from product_sales_planning.api.v1.feishu_setup import setup_feishu_login, check_feishu_config
setup_feishu_login("cli_xxx_your_app_id", "your_app_secret", enable=True)
check_feishu_config()
```

Expected: `✅ 已创建飞书登录配置` or `✅ 已更新飞书登录配置`.

## 3. Feishu Open Platform Callback
Configure redirect URI in Feishu app settings:

`http://localhost:8080/api/method/product_sales_planning.api.v1.feishu_login.callback`

If using domain/proxy in production, replace with your real external URL.

## 4. Refresh and Verify
Run:

```bash
bench --site frontend clear-cache
bench restart
```

Then open:

- `http://localhost:8080/login`
- click Feishu login

## 5. Optional: Auto-init via site config
`product_sales_planning/install.py` already auto-inits Feishu if these keys exist:

- `feishu_app_id`
- `feishu_app_secret`

Set them to avoid manual setup after reinstall/migration.

## 6. Migrate + Auto-init (Recommended for local)
Use the helper script in this repo to run migration and Feishu login setup in one step:

```powershell
$env:FEISHU_APP_ID="cli_xxx_your_app_id"
$env:FEISHU_APP_SECRET="your_app_secret"
.\scripts\migrate_with_feishu_login.ps1 -SiteName frontend -BackendContainer frappe_docker-backend-1
```

What it does:
- `bench --site frontend migrate`
- `setup_feishu_login(...)`
- `check_feishu_config()`
- `bench --site frontend clear-cache`

## 7. New Server (Using Image) - Reconfigure Feishu Key
If you deploy to a new server using image only (new DB/site data), you need to set Feishu key again.

Run on server:

```bash
docker exec -i frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend console" <<'PY'
from product_sales_planning.api.v1.feishu_setup import setup_feishu_login, check_feishu_config
setup_feishu_login("your_feishu_app_id", "your_feishu_app_secret", enable=True)
check_feishu_config()
PY
```

Then clear cache:

```bash
docker exec -i frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend clear-cache"
```

Feishu callback URL on new server should be:

`https://your-domain/api/method/product_sales_planning.api.v1.feishu_login.callback`
