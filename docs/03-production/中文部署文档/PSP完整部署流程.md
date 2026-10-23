# PSP 完整部署流程（2026-07-17 校准）

> 本文由 2026-07-17 一次端到端排查（"v1.1.0 镜像疑似旧代码"）校准，固化了构建、推送、部署、验证、workspace 同步全链路的正确做法与坑点。
> 镜像、推送、服务器拉取、容器运行、代码内容全部经实测验证无误；"旧代码"误判源于版本号陷阱与 workspace 数据库未同步。

---

## 0. 五个必须先记住的认知（全是踩过的坑）

1. **构建环境是 WSL Ubuntu-24.04，不是 Windows PowerShell**。Docker 装在 WSL，`docker build` 必须同时加 `--network=host` **和** `--build-arg HTTP_PROXY/HTTPS_PROXY`，两者缺一不可：
   - `--network=host` 让容器内 `127.0.0.1:7897` 指向宿主 clash 代理（否则 127.0.0.1 是容器自己）；
   - 但 **BuildKit 不会继承宿主的 `http_proxy`/`https_proxy` 环境变量**（实测：不传 `--build-arg` 时容器内 `env` 里没有任何代理变量），而 github.com 直连被墙。只加 `--network=host` 的话，`bench init` clone frappe 会卡 134 秒后失败：`InvalidRemoteException: Invalid frappe path`，偶尔表现为 `GnuTLS recv error (-110)`。
   - `scripts/update-frappe-only.sh` 已内置这两个参数（代理地址可用 `BUILD_PROXY` 覆盖）。手动 `docker build` 时务必照抄。
2. **apps.json 用 `--secret` 注入**（新版 Containerfile），不再用 `APPS_JSON_BASE64`。`CACHE_BUST` 改值才刷新 frappe 层；改了 apps.json 也必须改 `CACHE_BUST`。
3. **psp 仓库三分支：`develop`（开发主线）-> `main`（定期合并 develop）-> `master`（废弃）**。`apps.json` 配 `branch: main`，所以构建前必须确认 main 已合并 develop 最新代码。
4. **版本号 `0.0.1` 是无效指标**！psp 的 `__version__` 永远是 `0.0.1`，新旧都一样。判断代码新旧只能用**具体文件 md5**。
5. **workspace 是「文件 + 数据库」双份**。镜像里文件更新了，`bench migrate` 也不会覆盖数据库里已有的 workspace 记录。改了 workspace 必须手动删旧记录 + 重新同步。

---

## 1. 构建前：确认代码源头已到位

```bash
# 在 WSL 里（能访问 codeup）
URL=https://codeup.aliyun.com/64c8b550dcc8d50d3cc7f5b4/jack571754/product_sales_planning.git
git ls-remote $URL refs/heads/main refs/heads/develop

# 本地 clone 对比 main 是否已含 develop 全部新代码
git clone --branch main "$URL" /tmp/psp-check && cd /tmp/psp-check
git fetch origin develop:develop
git log --oneline main..develop     # 必须为空 -> main 已含 develop 全部新代码
```

若不为空：先在 codeup 把 develop 合并到 main，再构建。否则镜像拉到的是 main 上的旧代码。

---

## 2. 构建镜像（WSL）

```bash
wsl -d Ubuntu-24.04
bash /mnt/d/project/02-开源项目/frappe_docker/scripts/update-frappe-only.sh
```

脚本自动完成：
- ① 检查基础镜像 `frappe/{build,base}:version-16` 存在；
- ② 复制干净 context（仅 `images/ resources/ apps.json`）+ 修 CRLF；
- ③ `docker build --network=host --build-arg HTTP_PROXY=http://127.0.0.1:7897 --build-arg HTTPS_PROXY=http://127.0.0.1:7897 --build-arg NO_PROXY=localhost,127.0.0.1,::1 --secret=id=apps_json,src=apps.json --build-arg=CACHE_BUST=<时间戳> --build-arg=FRAPPE_BRANCH=version-16`；
- ④ 跑 `bench version` 验证。

产出临时 tag `tmp-frappe-update`，约 5–15 分钟。

---

## 3. 验证镜像内容（用 md5，**不要用版本号**）

```bash
REG=crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/frappev16
docker run --rm --entrypoint=bash $REG:tmp-frappe-update -c \
  'md5sum /home/frappe/frappe-bench/apps/product_sales_planning/product_sales_planning/planning_system/doctype/tasks_store/tasks_store.json'
# 必须等于 develop 上的 md5（本次 v1.1.0 为 40a49927c6aadff9efeb9b82d54e2323）
```

md5 对得上 = 镜像就是最新代码。版本号显示 0.0.1 是正常的，忽略它。

---

## 4. 打 tag + 推送阿里云

```bash
FINAL_TAG=v1.1.1   # 延续序列，在已用最大 tag +1
docker tag  $REG:tmp-frappe-update $REG:${FINAL_TAG}
docker login --username=15309154328 $REG
docker push $REG:${FINAL_TAG}
```

---

## 5. 验证阿里云 == 本地（防止"推了但没推上去"）

```bash
docker pull $REG:${FINAL_TAG}
# Status: Image is up to date -> 远端 digest == 本地，推送成功
docker image inspect $REG:${FINAL_TAG} --format '{{.Id}}'   # 记下 digest
```

---

## 6. 服务器部署（backup: 172.16.200.44）

```bash
ssh root@172.16.200.44
/root/gitops/deploy-update.sh ${FINAL_TAG}

# 等价于本地脚本（若服务器 compose 文件是 erpnext-ip.yaml 而非 psp-ip.yaml）：
# COMPOSE_FILE=/root/gitops/erpnext-ip.yaml /root/gitops/deploy-psp.sh ${FINAL_TAG}
```

脚本自动：备份 -> sed 改 compose 里镜像 tag -> pull -> `up -d` -> 等 backend 就绪 -> `migrate` -> `clear-cache`。

---

## 7. 服务器验证（三方 digest 必须一致）

```bash
# ① 服务器上的镜像 digest == 阿里云（第5步记的）
docker images --digests | grep frappev16 | grep ${FINAL_TAG}

# ② backend 容器实际跑的就是这个镜像（image id 一致）
docker inspect psp-backend-1 --format '{{.Image}} | {{.Config.Image}}'

# ③ 容器里代码 md5 == develop（确认拉到新代码，不是缓存旧镜像）
docker exec psp-backend-1 bash -lc \
  'md5sum /home/frappe/frappe-bench/apps/product_sales_planning/product_sales_planning/planning_system/doctype/tasks_store/tasks_store.json'
```

三条全中 = 镜像链路完全正确。若 md5 不符 -> `docker compose -p psp pull && up -d --force-recreate`。

---

## 8. workspace 同步（**改了 workspace 才需要**）

`migrate` 不覆盖已有 workspace。若本次发版改了 workspace 文件：

```bash
docker exec -it psp-backend-1 bash -lc '
cd /home/frappe/frappe-bench
SITE=psp.xajuzi.com

# ① 先诊断：看数据库里有哪些 psp workspace（只读）
bench --site $SITE mariadb -e "
SELECT name,label,module,is_standard,for_user,modified FROM tabWorkspace
WHERE module LIKE \"%Planning%\" OR module LIKE \"%Sales%\"
   OR label LIKE \"%规划%\" OR label LIKE \"%销售%\" OR name LIKE \"%product_sales%\";"

# ② 删除旧标准 workspace，让 migrate 从最新 app 文件重建
bench --site $SITE mariadb -e "
DELETE FROM tabWorkspace
WHERE (module LIKE \"%Planning%\" OR module LIKE \"%Sales%\"
   OR label LIKE \"%规划%\" OR label LIKE \"%销售%\" OR name LIKE \"%product_sales%\")
  AND for_user IS NULL;"

bench --site $SITE migrate
bench --site $SITE clear-cache
'
```

然后**浏览器 Ctrl+Shift+R 强刷或退出重登**（workspace 缓存还在前端/redis）。

---

## 9. 线上验收

```bash
curl -I https://psp.xajuzi.com
docker exec psp-backend-1 bash -lc 'bench --site psp.xajuzi.com list-apps'

# 防发版大坑：backend/frontend 的 desk.bundle CSS 哈希必须一致
docker exec psp-backend-1  sh -lc 'ls /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'
docker exec psp-frontend-1 sh -lc 'ls /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'
```

---

## 10. 回滚

```bash
/root/gitops/deploy-update.sh <旧tag>   # 用旧 tag 重跑部署脚本即可
```

---

## 速查表

| 项 | 值 |
|---|---|
| Registry | `crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723` |
| 镜像名 | `frappev16` |
| 构建机 | WSL Ubuntu-24.04（用户 frappe） |
| 构建脚本 | `scripts/update-frappe-only.sh` |
| 部署服务器 | `172.16.200.44`（backup） |
| 部署脚本 | `/root/gitops/deploy-update.sh <tag>` |
| compose project | `psp`，文件 `/root/gitops/psp-ip.yaml`（或 `erpnext-ip.yaml`） |
| 站点 | `psp.xajuzi.com` |
| backend 容器 | `psp-backend-1` |
| 验证用文件 | `planning_system/doctype/tasks_store/tasks_store.json`（md5 对比 develop） |
| 版本号 | **忽略**（永远 0.0.1，不能判断新旧） |

---

## 排障决策树（"线上代码是旧的？"）

```
怀疑线上是旧代码
  │
  ├─ 用版本号判断？ → 无效，0.0.1 永远不变。改用文件 md5。
  │
  ├─ 镜像里文件 md5 == develop？
  │    ├─ 否 → 构建问题：确认 main 已合并 develop（步骤1）、CACHE_BUST 已刷新
  │    └─ 是 → 镜像 OK，往下查
  │
  ├─ 阿里云 digest == 本地？（docker pull 后 id 不变）
  │    ├─ 否 → 推送问题：重新 push
  │    └─ 是 → 推送 OK，往下查
  │
  ├─ 服务器镜像 digest == 阿里云？容器 image id == 该镜像？
  │    ├─ 否 → 拉取/重建问题：docker compose pull && up -d --force-recreate
  │    └─ 是 → 服务器 OK，往下查
  │
  └─ 是 workspace / 前端没更新？
       ├─ workspace → 步骤 8：删旧记录 + migrate + 清缓存
       └─ 前端 → bench build + clear-cache + 浏览器强刷
```
