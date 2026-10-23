# product_sales_planning 构建、运行与迁移指南

目标：将 `product_sales_planning` 固化到自定义镜像，并确保可重复部署与可迁移。

## 1. 准备应用清单

编辑 `apps.demo.json`：

```json
[
  {
    "url": "https://github.com/jack571754/product_sales_planning.git",
    "branch": "main"
  }
]
```

## 2. 构建自定义镜像（PowerShell）

```powershell
$APPS_JSON_BASE64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content .\apps.demo.json -Raw)))
docker build --build-arg FRAPPE_PATH=https://github.com/frappe/frappe --build-arg FRAPPE_BRANCH=version-16 --build-arg APPS_JSON_BASE64="$APPS_JSON_BASE64" --tag product_sales_planning:v16-hotfix2 --file images/layered/Containerfile .
```

## 3. `.env` 基线

至少包含：

```env
CUSTOM_IMAGE=product_sales_planning
CUSTOM_TAG=v16-hotfix2
PULL_POLICY=missing
DB_PASSWORD=123
HTTP_PUBLISH_PORT=8080
FRAPPE_SITE_NAME_HEADER=frontend
```

同时建议：
- `overrides/compose.mariadb.yaml` 使用 `mariadb:10.6`（兼容现有数据卷）。
- backend/frontend 共享 `sites/assets` 卷。

## 4. 启动与迁移

```powershell
docker compose -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml up -d
wsl -d Ubuntu-24.04 -- docker exec frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend migrate && bench --site frontend clear-cache"
```

## 5. 验收

```powershell
wsl -d Ubuntu-24.04 -- docker exec frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend list-apps"
curl -I http://localhost:8080/
curl -I http://localhost:8080/planning
curl -I http://localhost:8080/assets/product_sales_planning/planning/manifest.json
```

预期：
- `list-apps` 包含 `product_sales_planning`
- `/` 返回 `200`
- `/planning` 未登录时跳转登录页
- `manifest.json` 返回 `200`

## 6. 当前镜像完整迁移说明

当前关键卷：
- `frappe_docker_sites`
- `frappe_docker_sites-assets`
- `frappe_docker_db-data`

### 6.1 源机器导出

```bash
docker save product_sales_planning:v16-hotfix2 -o product_sales_planning_v16-hotfix2.tar
docker exec -it frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend backup --with-files"
```

### 6.2 目标机器导入

```bash
docker load -i product_sales_planning_v16-hotfix2.tar
docker compose -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml up -d
```

如需恢复备份：

```bash
docker exec -it frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend restore <db_backup.sql.gz> --force && bench --site frontend migrate --skip-search-index && bench --site frontend clear-cache"
```

## 7. 常见错误

- `open Dockerfile: no such file or directory`：缺少 `--file images/layered/Containerfile`
- `flag needs an argument: --build-arg`：PowerShell 命令断行，改为单行
- 全站 `404`：`FRAPPE_SITE_NAME_HEADER` 未设为 `frontend`
- Desk 图标点不开（Icon is not correctly configured）：Workspace Sidebar 首个可跳转链接失效，需要清理无效链接并清缓存
