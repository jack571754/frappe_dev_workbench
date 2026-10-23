# Frappe Docker 开发与更新最佳实践（当前项目）

适用环境：`D:\project\frappe_docker`，站点 `frontend`，访问地址 `http://localhost:8080`。

## 1. 核心原则

1. 正式开发不要依赖“容器内临时改代码”。
2. 代码变更统一走：`Git -> 构建镜像 -> docker compose up -> migrate`。
3. 数据持久化靠 Docker Volume，不靠容器文件系统。

## 2. 当前持久化挂载（已验证）

- 站点数据：`/home/frappe/frappe-bench/sites`  
  对应：`/var/lib/docker/volumes/frappe_docker_sites/_data`
- 静态资源：`/home/frappe/frappe-bench/sites/assets`  
  对应：`/var/lib/docker/volumes/frappe_docker_sites-assets/_data`
- 数据库：`/var/lib/mysql`  
  对应：`/var/lib/docker/volumes/frappe_docker_db-data/_data`

说明：`/home/frappe/frappe-bench/apps` 不是持久卷，来自镜像层，重建容器会恢复为镜像内容。

## 3. 标准开发更新流程

1. 在应用仓库改代码并提交（如 `product_sales_planning`）。
2. 更新 `apps.demo.json`（仓库 URL/分支变更时）。
3. 构建新镜像（PowerShell 一行）：

```powershell
$APPS_JSON_BASE64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content .\apps.demo.json -Raw)))
docker build --build-arg FRAPPE_PATH=https://github.com/frappe/frappe --build-arg FRAPPE_BRANCH=version-16 --build-arg APPS_JSON_BASE64="$APPS_JSON_BASE64" --tag product_sales_planning:v16-hotfix2 --file images/layered/Containerfile .
```

4. 更新 `.env`：
- `CUSTOM_IMAGE=product_sales_planning`
- `CUSTOM_TAG=v16-hotfix2`
- `FRAPPE_SITE_NAME_HEADER=frontend`

5. 启动并执行迁移：

```powershell
docker compose -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml up -d
wsl -d Ubuntu-24.04 -- docker exec frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend migrate && bench --site frontend clear-cache"
```

## 4. 验收清单

```powershell
wsl -d Ubuntu-24.04 -- docker exec frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site frontend list-apps"
curl -I http://localhost:8080/
curl -I http://localhost:8080/planning
curl -I http://localhost:8080/assets/product_sales_planning/planning/manifest.json
```

## 5. 常见错误与修复

- `open Dockerfile: no such file`：缺少 `--file images/layered/Containerfile`。
- `flag needs an argument: --build-arg`：PowerShell 命令被断行，改成单行执行。
- Desk 图标点不开（Icon is not correctly configured）：通常是 Workspace Sidebar 首个可跳转链接失效，清理 Sidebar 无效链接并 `clear-cache`。
