# 部署方案优化报告（v2）

日期：2026-03-03  
范围：`D:\project\frappe_docker`（Frappe Docker + `frontend` 站点 + `product_sales_planning`）

## 1. 结论（先看这个）

当前环境已“可运行”，但未达到“可重复部署”。  
核心问题不是代码本身，而是**部署链路不闭环**：

1. `backend` 与 `frontend` 容器看到的 `apps` 不一致。  
2. 自定义 app 静态资源未被稳定发布到 `frontend` 可服务路径。  
3. 依赖手工修复（clone/install/copy），重建后会回退。

## 1.1 当前执行状态（2026-03-03 已落地）

已完成并生效：

1. 服务镜像统一为 `product_sales_planning:v16-hotfix1`（`backend/frontend/websocket` 已验证）。  
2. `compose.yaml` 已增加共享卷 `sites-assets`，并挂载到 backend/frontend。  
3. `.env` 已固定 `FRAPPE_SITE_NAME_HEADER=frontend`，`localhost` 访问不再全站 404。  
4. `overrides/compose.mariadb.yaml` 已固定 `mariadb:10.6`（兼容现有数据卷）。  
5. `/assets/product_sales_planning/planning/manifest.json` 已返回 `200`。  

仍为过渡项：

1. `v16-hotfix1` 来源于 `docker commit`，不可作为长期生产镜像治理方案。  
2. `/planning` 的资源发布目前仍依赖运行时发布逻辑，建议迁移为 CI 构建产物。

## 2. 现场确认（已验证）

- 站点 `frontend` 已安装 app：`frappe / erpnext / product_sales_planning`
- `frontend` 容器的 `/home/frappe/frappe-bench/apps` 仅有 `frappe, erpnext`
- `/planning` 白屏根因：`/assets/product_sales_planning/...` 404
- 临时修复后资源可访问（`manifest.json` 200），但仍属过渡态

## 3. 风险分级

## P0（立即整改）

1. 不可重复部署：自定义 app 未固化到统一镜像。  
2. 资源发布断链：`frontend` 无法稳定读取自定义 app 资产。  
3. 凭据安全：PAT 曾明文出现在终端历史，必须旋转。

## P1（本周整改）

1. 代理变量污染 `apt/pip/yarn`。  
2. PowerShell 多行命令易截断，导致误操作。  
3. 主机 conda 噪音影响排障效率。

## 4. 目标架构（推荐）

1. 用 `apps.demo.json` + `images/layered/Containerfile` 构建统一自定义镜像。  
2. `backend/frontend/websocket/queue/scheduler` 全部使用同一 `CUSTOM_IMAGE:CUSTOM_TAG`。  
3. 部署后只做站点动作：`install-app`（首次）、`migrate`、`clear-cache`。  
4. 前端构建统一在 Linux/WSL 执行，禁止在 UNC 路径直接跑 Node 构建。

补充约束（本仓库）：

1. 访问头固定：`FRAPPE_SITE_NAME_HEADER=frontend`。  
2. `sites/assets` 必须是 backend/frontend 共享卷，不使用匿名卷分裂。  
3. 数据卷沿用历史数据时，MariaDB 版本必须与数据格式兼容（当前为 `10.6`）。

## 5. 分阶段实施计划

## Phase A（当天完成）

1. 旋转 GitHub PAT，删除历史 token。  
2. 固化镜像并更新 `.env`：
   - `CUSTOM_IMAGE=<你的镜像名>`
   - `CUSTOM_TAG=<版本号>`
   - `PULL_POLICY=missing`
3. 重建：
   - `docker compose down`
   - `docker compose up -d --force-recreate`
4. 验证：
   - `bench --site frontend list-apps`
   - `curl -I http://localhost:8080/assets/product_sales_planning/planning/manifest.json`
   - 登录后访问 `/planning`

## Phase B（1周内）

1. 增加一键验收脚本（健康检查 + 关键 URL 200 校验）。  
2. 固化构建文档（仅一行 PowerShell 命令，避免换行问题）。  
3. CI 增加 smoke test：容器启动后检测 `/planning` 关键资源。

## 6. 回滚方案

出现不可恢复问题时：

1. 回退 `CUSTOM_IMAGE:CUSTOM_TAG` 到上一个可用版本。  
2. `docker compose up -d --force-recreate`。  
3. 执行：
   - `bench --site frontend migrate`
   - `bench --site frontend clear-cache`

## 7. 运维检查清单（每日/变更后）

1. `docker ps` 所有核心服务为 Up。  
2. `bench --site frontend list-apps` 含 `product_sales_planning`。  
3. `/assets/product_sales_planning/...` 返回 200。  
4. 后端日志无：
   - `ModuleNotFoundError: product_sales_planning`
   - 大量静态 404

## 8. 验收标准（Done 定义）

1. `docker compose down && up -d` 后无需任何手工拷贝。  
2. 重启任意单容器后 `/planning` 仍可访问。  
3. 新机器按文档一次部署成功。  
4. 连续 3 次重建结果一致。

## 9. 下一步（生产化）

1. 旋转并吊销历史 PAT（强制）。  
2. 用 `images/layered/Containerfile` 重建“可复现”镜像（替代 `v16-hotfix1`）。  
3. 将 `/planning` 资源发布纳入构建阶段，避免运行时手工补丁。  
4. 增加备份、监控、告警、恢复演练后再进入生产门槛评估。
