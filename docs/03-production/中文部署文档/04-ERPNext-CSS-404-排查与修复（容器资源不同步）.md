# ERPNext CSS 404 排查与修复（容器资源不同步）

## 1. 适用场景

- 页面可以打开，但样式明显错乱。
- 浏览器网络面板里 `/assets/...css` 返回 `404`，而 API、Socket.IO、部分 JS 正常。
- 在 `backend` 容器执行过 `bench build` 之后，页面开始引用新的静态资源哈希，但 `frontend` 仍然只能提供旧文件。

本文基于一次真实线上案例整理，适用于使用统一 `frappe/erpnext` 镜像部署的环境。

## 2. 已知环境

- 主机名：`backup`
- 当前用户：`root`
- Docker Compose 项目名：`erpnext`
- 访问域名：`psp.xajuzi.com`
- `frontend` 端口映射：`8080:8080`
- 国内服务器，无法访问 `github.com`
- 容器命名规则：`erpnext-{service}-1`

容器内关键路径：

```text
/home/frappe/frappe-bench/
├── apps/
│   ├── frappe/
│   ├── erpnext/
│   └── product_sales_planning/
├── sites/
│   ├── assets/
│   │   ├── frappe -> /home/frappe/frappe-bench/apps/frappe/frappe/public
│   │   ├── erpnext -> /home/frappe/frappe-bench/apps/erpnext/erpnext/public
│   │   ├── product_sales_planning -> /home/frappe/frappe-bench/apps/product_sales_planning/product_sales_planning/public
│   │   ├── assets.json
│   │   ├── assets-rtl.json
│   │   ├── css/
│   │   ├── js/
│   │   └── locale/
│   ├── common_site_config.json
│   └── currentsite.txt
└── logs/
```

## 3. 问题现象

现象链条如下：

1. 页面 HTML 引用了新的 CSS 哈希文件。
2. `frontend` 容器中只有旧哈希文件。
3. 请求新 CSS 路径时返回 `404`。
4. 页面因此无样式或样式残缺。

典型对比示意：

| 文件 | HTML 引用 | frontend 实际存在 | 说明 |
| --- | --- | --- | --- |
| `desk.bundle.css` | 新哈希 | 旧哈希 | 404 主因 |
| `report.bundle.css` | 新哈希 | 旧哈希 | 404 主因 |
| `desk.bundle.js` | 未变化 | 同名文件存在 | 因此 JS 可能看起来正常 |

## 4. 根因判断

基于当前信息，更接近真实根因的是“静态资源产物不同步”，而不只是“没共享 `sites` 卷”这么简单。

### 4.1 为什么不是单纯的 Nginx 或域名问题

- CSS 请求精确返回 `404`，不是 `502` 或反向代理超时。
- API、Socket.IO、部分 JS 正常，说明服务整体可达。
- 这类问题更像“页面引用的文件名”和“磁盘上的真实文件名”不一致。

### 4.2 为什么只同步 `sites/assets` 往往不够

当前环境中：

```text
sites/assets/frappe -> apps/frappe/frappe/public
sites/assets/erpnext -> apps/erpnext/erpnext/public
```

也就是说，`sites/assets/frappe/dist/...` 的真实落点通常是：

```text
/home/frappe/frappe-bench/apps/frappe/frappe/public/dist
/home/frappe/frappe-bench/apps/erpnext/erpnext/public/dist
```

如果只打包 `sites/assets`，很可能只是复制了符号链接本身，而不是复制 `dist` 目录中的真实新文件。

### 4.3 和仓库默认编排的关系

- `compose.yaml` 默认给 `backend` 和 `frontend` 都挂载了 `sites:/home/frappe/frappe-bench/sites`。
- 但镜像构建里又声明了 `VOLUME /home/frappe/frappe-bench/sites/assets`，历史部署中可能残留独立 `assets` 卷。
- 一旦旧 `assets` 卷、旧镜像内容、以及新生成的 `assets.json` 混在一起，就容易出现“HTML 已切到新哈希，但 `frontend` 仍在提供旧资源”的情况。

## 5. 关于 `bench build` 的判断

本次现象里：

- `bench build` 虽然因为国内网络无法访问 GitHub 出现超时或下载异常提示；
- 但本地 `esbuild` 已经成功执行；
- 而且新的 CSS 哈希确实已经生成。

因此：

- GitHub 超时不是这次 CSS `404` 的主因；
- 真正的主因仍然是新旧资源没有在同一套容器视图中保持一致。

### 5.1 本次真实大坑：不要只在生产环境 `backend` 执行 `bench build`

这次线上事故进一步确认了一个非常容易踩坑的点：

- `sites` 是共享卷；
- 但 `apps/frappe/frappe/public/dist`、`apps/.../public/dist`、以及自定义应用 `public` 目录并不是天然共享的；
- 如果只在 `backend` 容器里执行 `bench build`，`sites/assets/assets.json` 可能已经更新为新哈希；
- 但 `frontend` 容器仍然只持有旧的 `public/dist` 文件；
- 最终就会出现 “manifest 已经切到新文件名，但 nginx 还在提供旧文件” 的撕裂状态。

这类问题的典型表现是：

1. `Desk` 页面的 `desk.bundle.*.css`、`report.bundle.*.css` 返回 `404`；
2. `/planning` 之类的自定义页面出现白屏、布局错乱、局部样式丢失；
3. 浏览器里能看到 HTML、API、Socket.IO 都正常，但 CSS/部分前端资源命中 `404`；
4. `backend` 和 `frontend` 容器里同一路径下的哈希文件不一致。

建议优先用下面三组命令做“后端产物 / 前端产物 / manifest”三方对比：

```bash
docker exec erpnext-backend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'
docker exec erpnext-frontend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'
docker exec erpnext-frontend-1 sh -lc 'grep -o "desk.bundle.[A-Z0-9]*.css" /home/frappe/frappe-bench/sites/assets/assets.json | head'
```

如果输出像下面这样，就说明已经发生了“单边构建”：

- `backend` 里是 `desk.bundle.ZXRVYH56.css`
- `frontend` 里还是 `desk.bundle.ZASSBZMM.css`
- `assets.json` 已经引用 `desk.bundle.ZXRVYH56.css`
- 此时请求 `frontend` 的新哈希文件会直接 `404`

换句话说，这次问题不是“重新 build 一下就好”，而是：

> 在生产环境只对 `backend` 执行了 `bench build`，导致共享的 `assets.json` 指向新哈希，但 `frontend` 还在提供旧的 `public/dist` 文件。

### 5.2 `sites/assets` 权限错误会让问题更隐蔽

这次排障里还遇到了第二个坑：`sites/assets`、`sites/assets/locale`、`logs` 被 `root` 接管后，`bench build --force` 可能会出现“半成功”状态：

- `esbuild` 已生成新的 `dist` 文件；
- `assets.json` 可能已被改写；
- 但符号链接、locale 编译、部分写入操作报 `Permission denied`；
- 最终表面上像是 “build 跑过了”，实际上 manifest、权限和容器视图已经不一致。

生产环境建议先把 `sites` 与 `logs` 统一交回 `frappe`：

```bash
docker compose --project-name erpnext -f /root/gitops/erpnext-ip.yaml exec -u root backend \
  bash -lc 'chown -R frappe:frappe /home/frappe/frappe-bench/sites /home/frappe/frappe-bench/logs'
```

如果不先处理权限，后续哪怕手工改对了 `assets.json`，也仍可能在下一次 `bench build` 时再次写出不完整状态。

## 6. 先确认，再修复

建议先执行下面这组低风险诊断命令，确认到底是卷问题、镜像版本问题，还是 `public/dist` 没同步。

### 6.1 找到实际 compose 文件路径

```bash
docker inspect erpnext-frontend-1 --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}'
docker inspect erpnext-frontend-1 --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}'
```

### 6.2 对比两个容器的真实挂载

```bash
docker inspect erpnext-backend-1 --format '{{range .Mounts}}{{println .Destination " -> " .Type ":" .Name ":" .Source}}{{end}}'
docker inspect erpnext-frontend-1 --format '{{range .Mounts}}{{println .Destination " -> " .Type ":" .Name ":" .Source}}{{end}}'
```

重点看：

- 两边是否都挂了 `/home/frappe/frappe-bench/sites`
- `frontend` 是否额外挂了 `/home/frappe/frappe-bench/sites/assets`

### 6.3 确认是不是同一镜像版本

```bash
docker inspect erpnext-backend-1 --format '{{.Config.Image}} -> {{.Image}}'
docker inspect erpnext-frontend-1 --format '{{.Config.Image}} -> {{.Image}}'
docker inspect erpnext-websocket-1 --format '{{.Config.Image}} -> {{.Image}}'
```

如果镜像摘要不同，说明前后端根本不在同一版镜像上。

### 6.4 检查符号链接真实落点

```bash
docker exec erpnext-backend-1 sh -lc 'readlink -f /home/frappe/frappe-bench/sites/assets/frappe'
docker exec erpnext-frontend-1 sh -lc 'readlink -f /home/frappe/frappe-bench/sites/assets/frappe'
```

### 6.5 直接比较真实 `dist` 目录里的哈希

```bash
docker exec erpnext-backend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'
docker exec erpnext-frontend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'

docker exec erpnext-backend-1 sh -lc 'grep -o "desk.bundle.[A-Z0-9]*.css" /home/frappe/frappe-bench/sites/assets/assets.json | head'
docker exec erpnext-frontend-1 sh -lc 'grep -o "desk.bundle.[A-Z0-9]*.css" /home/frappe/frappe-bench/sites/assets/assets.json | head'

docker exec erpnext-backend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep report.bundle'
docker exec erpnext-frontend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep report.bundle'
docker exec erpnext-frontend-1 sh -lc 'grep -o "report.bundle.[A-Z0-9]*.css" /home/frappe/frappe-bench/sites/assets/assets.json | head'

curl -I http://127.0.0.1:8085/assets/product_sales_planning/planning/manifest.json
```

如果 `backend` 的 `public/dist` 和 `assets.json` 是新哈希，而 `frontend` 还是旧哈希，就可以确认是资源不同步。

## 7. 临时修复：直接同步真实构建产物

适用场景：

- 需要尽快恢复线上页面；
- 暂时没有停机窗口做结构性修复；
- 已确认 `backend` 内确实生成了正确的新资源。

### 7.1 从 backend 导出真实 `dist`

```bash
docker exec erpnext-backend-1 sh -lc 'tar czf /tmp/frappe-dist.tgz -C /home/frappe/frappe-bench/apps/frappe/frappe/public dist'
docker exec erpnext-backend-1 sh -lc 'tar czf /tmp/erpnext-dist.tgz -C /home/frappe/frappe-bench/apps/erpnext/erpnext/public dist'
docker exec erpnext-backend-1 sh -lc 'tar czf /tmp/psp-public.tgz -C /home/frappe/frappe-bench/apps/product_sales_planning/product_sales_planning public'

docker cp erpnext-backend-1:/tmp/frappe-dist.tgz /tmp/frappe-dist.tgz
docker cp erpnext-backend-1:/tmp/erpnext-dist.tgz /tmp/erpnext-dist.tgz
docker cp erpnext-backend-1:/tmp/psp-public.tgz /tmp/psp-public.tgz

docker cp erpnext-backend-1:/home/frappe/frappe-bench/sites/assets/assets.json /tmp/assets.json
docker cp erpnext-backend-1:/home/frappe/frappe-bench/sites/assets/assets-rtl.json /tmp/assets-rtl.json
```

### 7.2 复制到 frontend 并覆盖

```bash
docker cp /tmp/frappe-dist.tgz erpnext-frontend-1:/tmp/frappe-dist.tgz
docker cp /tmp/erpnext-dist.tgz erpnext-frontend-1:/tmp/erpnext-dist.tgz
docker cp /tmp/psp-public.tgz erpnext-frontend-1:/tmp/psp-public.tgz
docker cp /tmp/assets.json erpnext-frontend-1:/tmp/assets.json
docker cp /tmp/assets-rtl.json erpnext-frontend-1:/tmp/assets-rtl.json

docker exec erpnext-frontend-1 sh -lc 'rm -rf /home/frappe/frappe-bench/apps/frappe/frappe/public/dist && tar xzf /tmp/frappe-dist.tgz -C /home/frappe/frappe-bench/apps/frappe/frappe/public'
docker exec erpnext-frontend-1 sh -lc 'rm -rf /home/frappe/frappe-bench/apps/erpnext/erpnext/public/dist && tar xzf /tmp/erpnext-dist.tgz -C /home/frappe/frappe-bench/apps/erpnext/erpnext/public'
docker exec erpnext-frontend-1 sh -lc 'tar xzf /tmp/psp-public.tgz -C /home/frappe/frappe-bench/apps/product_sales_planning/product_sales_planning'
docker exec erpnext-frontend-1 sh -lc 'cp /tmp/assets.json /home/frappe/frappe-bench/sites/assets/assets.json && cp /tmp/assets-rtl.json /home/frappe/frappe-bench/sites/assets/assets-rtl.json'

docker restart erpnext-frontend-1
```

补充说明：

- `frappe/public/dist` 解决的是 Desk、Report、Login 等 Frappe 核心静态资源；
- 自定义应用如果也在生产容器里重新构建过，必须一并同步它的 `public` 目录；
- 本次案例里需要同步的是 `product_sales_planning/product_sales_planning/public`，否则 `/planning` 相关资源仍可能继续错乱。

### 7.3 修复后验证

```bash
docker exec erpnext-backend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'
docker exec erpnext-frontend-1 sh -lc 'ls -1 /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css | grep desk.bundle'
docker exec erpnext-frontend-1 sh -lc 'grep -o "desk.bundle.[A-Z0-9]*.css" /home/frappe/frappe-bench/sites/assets/assets.json | head'
docker exec erpnext-frontend-1 sh -lc 'grep -o "report.bundle.[A-Z0-9]*.css" /home/frappe/frappe-bench/sites/assets/assets.json | head'
curl -I http://127.0.0.1:8085/assets/product_sales_planning/planning/manifest.json
docker logs --tail=50 erpnext-frontend-1
```

判定标准：

- `backend` 与 `frontend` 中 `desk.bundle.*.css` / `report.bundle.*.css` 哈希一致；
- `assets.json` 中引用的 CSS 哈希，和 `frontend` 的 `public/dist/css` 中的文件名一致；
- 自定义应用的 `manifest.json`、页面入口资源可以返回 `200`；
- `frontend` 日志不再出现对应 CSS 文件 `404`；
- 浏览器强刷后页面样式恢复。

## 8. 永久修复：清理旧 assets 视图并统一镜像版本

如果确认 `frontend` 有独立的 `sites/assets` 卷，或者不同服务镜像摘要不一致，建议安排停机窗口做永久修复。

### 8.1 确认 assets 卷名

```bash
docker inspect erpnext-frontend-1 --format '{{range .Mounts}}{{println .Destination " -> " .Name}}{{end}}'
```

### 8.2 停服务

将下面的 `<compose-file>` 替换为 6.1 中查到的实际 compose 文件路径：

```bash
docker compose -p erpnext -f <compose-file> down
```

### 8.3 仅删除旧 assets 卷

```bash
docker volume rm <assets_volume_name>
```

注意：

- 不要删除 `sites` 卷；
- 不要删除数据库相关卷；
- 如果卷被占用，先用 `docker ps -a --filter volume=<assets_volume_name>` 找出占用容器。

### 8.4 用同一 tag 重建

```bash
docker compose -p erpnext -f <compose-file> up -d
docker compose -p erpnext -f <compose-file> restart frontend backend websocket
```

### 8.5 清缓存

站点名按实际替换：

```bash
docker compose -p erpnext -f <compose-file> exec backend \
sh -lc 'bench --site <site-name> clear-cache && bench --site <site-name> clear-website-cache'
```

## 9. 长期建议

1. 不要把在生产容器里执行 `bench build` 当成常规修复手段。
2. 自定义应用和静态资源应尽量在镜像构建阶段预编译。
3. `backend`、`frontend`、`websocket` 发布时必须使用同一个镜像 tag。
4. 如果生产环境不得不执行 `bench build`，执行后必须立即把 `frappe/public/dist` 和受影响应用的 `public` 同步到 `frontend`。
5. 每次发布后固定检查三个服务的镜像摘要是否一致，并对比 `backend` / `frontend` 的 `public/dist` 哈希。
6. 若沿用旧部署历史，优先排查是否残留独立 `assets` 卷。
7. 把 `sites`、`sites/assets`、`logs` 的属主固定为 `frappe:frappe`，避免下次出现“manifest 已改但 build 半失败”。

## 10. 一句话结论

这次问题的本质不是“Frappe 前端本身坏了”，而是：

> 在生产环境只对 `backend` 执行了 `bench build`，共享的 `assets.json` 已切到新哈希，但 `frontend` 仍在提供旧的 `public/dist` 文件，于是 CSS/页面资源开始 `404`。

先用第 6 节确认差异，再根据现场风险选择第 7 节临时救火或第 8 节永久修复。
