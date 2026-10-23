# PSP 发版更新流程

本文档描述从本地构建镜像到服务器部署更新的完整流程。

## 1. 流程概览

```
本地开发环境
    ├── 1. 更新代码 (git push)
    ├── 2. 构建新镜像
    └── 3. 推送到阿里云镜像仓库
           ↓
服务器生产环境 (172.16.200.44)
    ├── 4. 备份数据
    ├── 5. 拉取新镜像
    ├── 6. 更新容器
    ├── 7. 执行迁移
    └── 8. 验证发布
```

## 2. 镜像版本规范

### 2.1 版本命名规则

```
frappev16:<VERSION>-psp-<DATE>-<BUILD>
```

示例：
- `frappev16:16.7.3-psp-20260318-001`
- `frappev16:16.7.3-psp-20260318-002`

### 2.2 镜像仓库地址

```
crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/frappev16
```

## 3. 本地构建流程

### 3.1 准备应用清单

确保 `apps.demo.json` 包含所有需要的应用：

```json
[
  {
    "url": "https://github.com/jack571754/product_sales_planning.git",
    "branch": "main"
  }
]
```

### 3.2 构建镜像

**PowerShell (Windows)：**

```powershell
# 设置变量
  

# 生成 apps.json 的 base64 编码
$APPS_JSON_BASE64 = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes((Get-Content .\apps.json -Raw))
  )
# 构建镜像
docker build `
  --build-arg FRAPPE_PATH=https://github.com/frappe/frappe `
  --build-arg FRAPPE_BRANCH=version-16 `
  --build-arg APPS_JSON_BASE64="$APPS_JSON_BASE64" `
  --tag "${REGISTRY}/frappev16:${TAG}" `
  --file images/layered/Containerfile .
```

**Bash (Linux/Mac)：**

```bash
# 设置变量
VERSION="v1.0.10"
DATE=$(date +%Y%m%d)
BUILD="001"
TAG="${VERSION}-psp-${DATE}-${BUILD}"
REGISTRY="crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723"

# 生成 apps.json 的 base64 编码
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)

# 构建镜像
docker build \
  --build-arg FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg FRAPPE_BRANCH=version-16 \
  --build-arg APPS_JSON_BASE64=$APPS_JSON_BASE64 \
  --tag "${REGISTRY}/frappev16:${TAG}" \
  --file images/layered/Containerfile .
```

### 3.3 推送镜像

```bash
# 登录阿里云镜像仓库
docker login --username=15309154328 crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com

# 推送镜像
docker push "${REGISTRY}/frappev16:${TAG}"

# 可选：同时推送 latest 标签
docker tag "${REGISTRY}/frappev16:${TAG}" "${REGISTRY}/frappev16:latest"
docker push "${REGISTRY}/frappev16:latest"
```

### 3.4 发版大坑：不要在生产环境只对 `backend` 执行 `bench build`

这次线上排障确认了一个非常关键的发布坑：

- `sites` 是共享的，所以 `sites/assets/assets.json` 会被所有容器一起看到；
- 但 `apps/frappe/frappe/public/dist` 和自定义应用 `public` 目录不是共享卷；
- 如果只在 `backend` 容器里执行 `bench build`，`assets.json` 会切到新哈希；
- `frontend` 容器却还在提供旧的静态资源文件；
- 最终 Desk 页面 CSS 404、布局错乱，自定义页面也可能白屏或样式残缺。

因此，生产发版的正确原则是：

1. 尽量在镜像构建阶段把前端资源编译好；
2. 不要把 `docker exec psp-backend-1 bench build` 当成线上常规动作；
3. 如果线上为了救火不得不在 `backend` build，一定要立即把构建产物同步到 `frontend`。

紧急同步命令如下。

**同步 Frappe 核心 dist：**

```bash
docker exec psp-backend-1 sh -lc 'tar czf /tmp/frappe-dist.tgz -C /home/frappe/frappe-bench/apps/frappe/frappe/public dist'
docker cp psp-backend-1:/tmp/frappe-dist.tgz /tmp/frappe-dist.tgz
docker cp /tmp/frappe-dist.tgz psp-frontend-1:/tmp/frappe-dist.tgz
docker exec psp-frontend-1 sh -lc 'rm -rf /home/frappe/frappe-bench/apps/frappe/frappe/public/dist && tar xzf /tmp/frappe-dist.tgz -C /home/frappe/frappe-bench/apps/frappe/frappe/public'
```

**同步自定义应用 `product_sales_planning` 的 `public`：**

```bash
docker exec psp-backend-1 sh -lc 'tar czf /tmp/psp-public.tgz -C /home/frappe/frappe-bench/apps/product_sales_planning/product_sales_planning public'
docker cp psp-backend-1:/tmp/psp-public.tgz /tmp/psp-public.tgz
docker cp /tmp/psp-public.tgz psp-frontend-1:/tmp/psp-public.tgz
docker exec psp-frontend-1 sh -lc 'tar xzf /tmp/psp-public.tgz -C /home/frappe/frappe-bench/apps/product_sales_planning/product_sales_planning'
```

同步完成后再执行：

```bash
docker compose --project-name psp -f /root/gitops/psp-ip.yaml exec backend \
sh -lc 'bench --site 172.16.200.44 clear-cache && bench --site 172.16.200.44 clear-website-cache'

docker compose --project-name psp -f /root/gitops/psp-ip.yaml restart frontend backend websocket
```

## 4. 服务器部署流程

### 4.1 登录服务器

```bash
ssh root@172.16.200.44
```

### 4.2 备份数据（重要！）

```bash
# 进入项目目录
cd /root/gitops

# 备份数据库和站点文件
docker exec psp-backend-1 bench --site 172.16.200.44 backup --with-files

#   - 站点：172.16.200.44
#   - 备份时间：2026-04-09 14:13:54
#   - 备份方式：bench --site 172.16.200.44 backup --with-files
#   - 最后一行明确显示成功：
#       - Backup for Site 172.16.200.44 has been successfully completed with files

#   生成了 4 个备份文件：

#   - 配置文件备份
#       - /home/frappe/frappe-bench/sites/172.16.200.44/private/backups/20260409_141350-172_16_200_44-
#         site_config_backup.json
#   - 数据库备份
#       - /home/frappe/frappe-bench/sites/172.16.200.44/private/backups/20260409_141350-172_16_200_44-database.sql.gz
#   - 公共文件备份
#       - /home/frappe/frappe-bench/sites/172.16.200.44/private/backups/20260409_141350-172_16_200_44-files.tar
#   - 私有文件备份
#       - /home/frappe/frappe-bench/sites/172.16.200.44/private/backups/20260409_141350-172_16_200_44-private-files.tar

# 查看备份文件
docker exec psp-backend-1 ls -la /home/frappe/frappe-bench/sites/172.16.200.44/private/backups/
```

### 4.3 拉取新镜像

```bash
# 设置新镜像标签
"${REGISTRY}/frappev16:${TAG}" 查看镜像标签
替换为新镜像标签

NEW_IMAGE="新标签"

# 登录镜像仓库
docker login --username=你的用户名 crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com

# 拉取新镜像
docker pull $NEW_IMAGE
```

### 4.4 停止旧容器

```bash
# 停止所有服务容器
docker stop psp-frontend-1
docker stop psp-backend-1
docker stop psp-websocket-1
docker stop psp-scheduler-1
docker stop psp-queue-short-1
docker stop psp-queue-long-1
```

### 4.5 删除旧容器

```bash
# 删除容器（数据卷不会被删除）
docker rm psp-frontend-1
docker rm psp-backend-1
docker rm psp-websocket-1
docker rm psp-scheduler-1
docker rm psp-queue-short-1
docker rm psp-queue-long-1
```

### 4.6 使用新镜像启动容器

**方法一：使用脚本启动（推荐）**

创建更新脚本 `/root/gitops/update-containers.sh`：

```bash
#!/bin/bash
set -e

IMAGE="crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/v1.0.10-psp-20260714-001"
NETWORK="psp-network"
SITES_VOL="psp_sites"
SITES_ASSETS_VOL="psp_sites_assets"

echo "Starting containers with image: $IMAGE"

# Frontend (手动管理，端口 8085)
docker run -d --name psp-frontend-1 \
    --network $NETWORK \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    -e BACKEND=backend:8000 \
    -e SOCKETIO=websocket:9000 \
    -e FRAPPE_SITE_NAME_HEADER=172.16.200.44 \
    -p 8085:8080 \
    $IMAGE \
    nginx-entrypoint.sh

# Backend
docker run -d --name psp-backend-1 \
    --network $NETWORK \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    $IMAGE

# WebSocket
docker run -d --name psp-websocket-1 \
    --network $NETWORK \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    $IMAGE \
    node /home/frappe/frappe-bench/apps/frappe/socketio.js

# Scheduler
docker run -d --name psp-scheduler-1 \
    --network $NETWORK \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    $IMAGE \
    bench schedule

# Queue Short
docker run -d --name psp-queue-short-1 \
    --network $NETWORK \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    $IMAGE \
    bench worker --queue short,default

# Queue Long
docker run -d --name psp-queue-long-1 \
    --network $NETWORK \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    $IMAGE \
    bench worker --queue long,default,short

echo "All containers started."
```

执行脚本：

```bash
chmod +x /root/gitops/update-containers.sh
/root/gitops/update-containers.sh
```

**方法二：逐个启动**

```bash
IMAGE="crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/frappev16:16.7.3-psp-20260318-001"
NETWORK="psp_default"

# Backend
docker run -d --name psp-backend-1 \
    --network $NETWORK \
    -v psp_sites:/home/frappe/frappe-bench/sites \
    -v psp_sites-assets:/home/frappe/frappe-bench/sites/assets \
    $IMAGE

# Frontend
docker run -d --name psp-frontend-1 \
    --network $NETWORK \
    -v psp_sites:/home/frappe/frappe-bench/sites \
    -v psp_sites-assets:/home/frappe/frappe-bench/sites/assets \
    -e BACKEND=backend:8000 \
    -e SOCKETIO=websocket:9000 \
    -e FRAPPE_SITE_NAME_HEADER=172.16.200.44 \
    -p 8085:8080 \
    $IMAGE \
    nginx-entrypoint.sh

# WebSocket
docker run -d --name psp-websocket-1 \
    --network $NETWORK \
    -v psp_sites:/home/frappe/frappe-bench/sites \
    $IMAGE \
    node /home/frappe/frappe-bench/apps/frappe/socketio.js

# Scheduler
docker run -d --name psp-scheduler-1 \
    --network $NETWORK \
    -v psp_sites:/home/frappe/frappe-bench/sites \
    -v psp_sites-assets:/home/frappe/frappe-bench/sites/assets \
    $IMAGE \
    bench schedule

# Queue Short
docker run -d --name psp-queue-short-1 \
    --network $NETWORK \
    -v psp_sites:/home/frappe/frappe-bench/sites \
    -v psp_sites-assets:/home/frappe/frappe-bench/sites/assets \
    $IMAGE \
    bench worker --queue short,default

# Queue Long
docker run -d --name psp-queue-long-1 \
    --network $NETWORK \
    -v psp_sites:/home/frappe/frappe-bench/sites \
    -v psp_sites-assets:/home/frappe/frappe-bench/sites/assets \
    $IMAGE \
    bench worker --queue long,default,short
```

### 4.7 执行数据库迁移

```bash
# 等待 backend 完全启动（约 30 秒）
sleep 30

# 执行迁移
docker exec psp-backend-1 bench --site 172.16.200.44 migrate

# 清除缓存
docker exec psp-backend-1 bench --site 172.16.200.44 clear-cache

# 如果有飞书配置，重新初始化（可选）
# docker exec psp-backend-1 bench --site 172.16.200.44 execute product_sales_planning.api.v1.feishu_setup.check_feishu_config
```

### 4.8 验证发布

```bash
# 检查容器状态
docker ps | grep psp

# 测试本地访问
curl -I http://127.0.0.1:8085

# 测试域名访问
curl -I https://psp.xajuzi.com

# 检查应用列表
docker exec psp-backend-1 bench --site 172.16.200.44 list-apps

# 对比 backend / frontend 的 Frappe 核心 CSS 哈希
docker exec psp-backend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle || true'
docker exec psp-frontend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle || true'
docker exec psp-frontend-1 sh -lc 'grep -o "desk.bundle.[A-Z0-9]*.css" /home/frappe/frappe-bench/sites/assets/assets.json | head'

# 检查自定义应用 manifest 是否正常返回
curl -I http://127.0.0.1:8085/assets/product_sales_planning/planning/manifest.json

# 查看后端日志
docker logs psp-backend-1 --tail 50

# 查看前端日志里是否还有 CSS 404
docker logs psp-frontend-1 --tail 50
```

## 5. 一键更新脚本

创建 `/root/gitops/deploy-update.sh`：

```bash
#!/bin/bash
set -e

# ==================== 配置区域 ====================
IMAGE="crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/frappev16"
TAG="${1:-latest}"  # 默认使用 latest，可通过参数指定版本
FULL_IMAGE="${IMAGE}:${TAG}"
NETWORK="psp_default"
SITES_VOL="psp_sites"
SITES_ASSETS_VOL="psp_sites-assets"
SITE_NAME="172.16.200.44"
FRONTEND_PORT="8085"
# =================================================

echo "=========================================="
echo "PSP 发版更新"
echo "镜像: ${FULL_IMAGE}"
echo "站点: ${SITE_NAME}"
echo "=========================================="

# 1. 备份
echo "[1/6] 备份数据..."
docker exec psp-backend-1 bench --site ${SITE_NAME} backup --with-files || echo "备份失败，继续..."

# 2. 拉取新镜像
echo "[2/6] 拉取新镜像..."
docker pull ${FULL_IMAGE}

# 3. 停止并删除旧容器
echo "[3/6] 停止旧容器..."
for container in frontend-1 backend-1 websocket-1 scheduler-1 queue-short-1 queue-long-1; do
    docker stop psp-${container} 2>/dev/null || true
    docker rm psp-${container} 2>/dev/null || true
done

# 4. 启动新容器
echo "[4/6] 启动新容器..."

# Backend
docker run -d --name psp-backend-1 \
    --network ${NETWORK} \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    ${FULL_IMAGE}

# Frontend
docker run -d --name psp-frontend-1 \
    --network ${NETWORK} \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    -e BACKEND=backend:8000 \
    -e SOCKETIO=websocket:9000 \
    -e FRAPPE_SITE_NAME_HEADER=${SITE_NAME} \
    -p ${FRONTEND_PORT}:8080 \
    ${FULL_IMAGE} \
    nginx-entrypoint.sh

# WebSocket
docker run -d --name psp-websocket-1 \
    --network ${NETWORK} \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    ${FULL_IMAGE} \
    node /home/frappe/frappe-bench/apps/frappe/socketio.js

# Scheduler
docker run -d --name psp-scheduler-1 \
    --network ${NETWORK} \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    ${FULL_IMAGE} \
    bench schedule

# Queue Short
docker run -d --name psp-queue-short-1 \
    --network ${NETWORK} \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    ${FULL_IMAGE} \
    bench worker --queue short,default

# Queue Long
docker run -d --name psp-queue-long-1 \
    --network ${NETWORK} \
    -v ${SITES_VOL}:/home/frappe/frappe-bench/sites \
    -v ${SITES_ASSETS_VOL}:/home/frappe/frappe-bench/sites/assets \
    ${FULL_IMAGE} \
    bench worker --queue long,default,short

# 5. 等待后端启动
echo "[5/6] 等待后端启动..."
sleep 30

# 6. 迁移
echo "[6/6] 执行迁移和清除缓存..."
docker exec psp-backend-1 bench --site ${SITE_NAME} migrate
docker exec psp-backend-1 bench --site ${SITE_NAME} clear-cache

# 验证
echo "=========================================="
echo "发布完成！"
echo "=========================================="
docker ps | grep psp
echo ""
echo "测试访问："
echo "  curl -I http://127.0.0.1:${FRONTEND_PORT}"
echo "  curl -I https://psp.xajuzi.com"
```

**使用方法：**

```bash
# 使用 latest 标签
/root/gitops/deploy-update.sh

# 指定版本标签
/root/gitops/deploy-update.sh 16.7.3-psp-20260318-001
```

## 6. 回滚流程

如果发布出现问题，可以快速回滚到之前的版本：

```bash
# 使用之前的镜像标签执行更新脚本
/root/gitops/deploy-update.sh 16.7.3-psp-20260317-001

# 或者从备份恢复
docker exec psp-backend-1 bench --site 172.16.200.44 restore /path/to/backup.sql.gz --force
docker exec psp-backend-1 bench --site 172.16.200.44 migrate
docker exec psp-backend-1 bench --site 172.16.200.44 clear-cache
```

## 7. 注意事项

1. **数据安全**
   - 发布前务必备份
   - 数据卷（`psp_sites`, `psp_sites-assets`, `psp_db-data`）不能删除

2. **停机时间**
   - 更新过程约需 1-2 分钟
   - 建议在业务低峰期发布

3. **镜像管理**
   - 保留最近 3-5 个版本的镜像，便于回滚
   - 定期清理旧镜像：`docker image prune -a --filter "until=720h"`

4. **监控验证**
   - 发布后检查日志：`docker logs psp-backend-1 --tail 100`
   - 验证关键功能：登录、飞书授权、核心业务流程
   - 额外检查 `backend` / `frontend` 的 `desk.bundle.*.css` 哈希是否一致

5. **禁止单边构建**
   - 禁止在生产环境只对 `backend` 执行 `bench build`
   - 若必须临时构建，必须同步 `frappe/public/dist` 与受影响应用 `public` 到 `frontend`
   - 如遇 `Permission denied`，先修复 `sites` / `logs` 属主为 `frappe:frappe`

---

**文档版本：** 2026-04-24
**适用环境：** PSP 生产环境
