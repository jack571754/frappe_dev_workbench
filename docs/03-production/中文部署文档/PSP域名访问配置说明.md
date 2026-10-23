# PSP 域名访问配置说明

## 1. 网络架构

```
用户浏览器
    ↓ HTTPS (psp.xajuzi.com)
网关服务器 (115.190.151.153)
    ↓ Nginx 反向代理
    ↓ HTTP (172.16.200.44:8085)
应用服务器 (172.16.200.44)
    └── Docker 容器群
        ├── frontend (nginx-entrypoint.sh)
        ├── backend (gunicorn)
        ├── websocket (socketio)
        ├── scheduler
        ├── queue-short
        └── queue-long
```

## 2. 域名与 DNS

| 项目 | 值 |
|------|-----|
| 域名 | `psp.xajuzi.com` |
| DNS 解析 | 指向 `115.190.151.153` (网关服务器) |
| 协议 | HTTPS (SSL 在网关层终止) |

## 3. 应用服务器配置 (172.16.200.44)

### 3.1 Docker 容器配置

**Frontend 容器（手动创建）：**

```bash
docker run -d --name erpnext-frontend-1 \
    --network erpnext_default \
    -v erpnext_sites:/home/frappe/frappe-bench/sites \
    -e BACKEND=backend:8000 \
    -e SOCKETIO=websocket:9000 \
    -e FRAPPE_SITE_NAME_HEADER=172.16.200.44 \
    -p 8085:8080 \
    crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/frappev16:16.7.3-psp-20260306-172949 \
    nginx-entrypoint.sh
```

**关键参数说明：**

| 参数 | 说明 |
|------|------|
| `--network erpnext_default` | 加入 erpnext 网络以访问 backend/websocket |
| `-p 8085:8080` | 映射端口 8085 到容器内部 8080 |
| `-e FRAPPE_SITE_NAME_HEADER` | 站点标识，与站点目录名一致 |

### 3.2 Frappe 站点配置

**设置域名：**

```bash
docker exec erpnext-backend-1 bench --site 172.16.200.44 set-config host_name "https://psp.xajuzi.com"
docker exec erpnext-backend-1 bench --site 172.16.200.44 clear-cache
```

**查看当前配置：**

```bash
docker exec erpnext-backend-1 bench --site 172.16.200.44 show-config
```

## 4. 网关服务器配置 (115.190.151.153)

### 4.1 Nginx 配置文件

**文件路径：** `/usr/local/nginx/conf-file/psp.conf`

```nginx
upstream psp_upstream {
    server 172.16.200.44:8085;
}

server {
    listen 443 ssl;
    server_name psp.xajuzi.com;

    # SSL 证书配置（根据实际情况修改）
    ssl_certificate /path/to/ssl/psp.xajuzi.com.pem;
    ssl_certificate_key /path/to/ssl/psp.xajuzi.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 客户端请求大小限制
    client_max_body_size 50m;

    location / {
        proxy_pass http://psp_upstream;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置
        proxy_read_timeout 120s;
        proxy_connect_timeout 60s;
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name psp.xajuzi.com;
    return 301 https://$server_name$request_uri;
}
```

### 4.2 Nginx 操作命令

```bash
# 测试配置
/usr/local/nginx/sbin/nginx -t

# 重载配置
/usr/local/nginx/sbin/nginx -s reload

# 查看错误日志
tail -f /usr/local/nginx/logs/error.log
```

## 5. 飞书登录配置

### 5.1 飞书开放平台配置

**访问地址：** https://open.feishu.cn/

**安全设置 → 重定向 URL：**

```
https://psp.xajuzi.com/api/method/product_sales_planning.api.v1.feishu_login.callback
```

### 5.2 Frappe Social Login Key 配置

登录 Frappe 后台（Desk）→ 搜索 "Social Login Key"：

| 字段 | 值 |
|------|-----|
| Social Login Provider | Custom |
| Provider Name | 飞书 |
| Client ID | (从飞书开放平台获取) |
| Client Secret | (从飞书开放平台获取) |
| Base URL | https://open.feishu.cn/open-apis |
| Redirect URL | https://psp.xajuzi.com/api/method/product_sales_planning.api.v1.feishu_login.callback |
| Enable | ☑️ |

### 5.3 环境变量（可选）

可通过环境变量传递飞书配置：

```bash
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
```

## 6. 常用操作命令

### 6.1 容器管理

```bash
# 查看容器状态
docker ps | grep erpnext

# 查看容器日志
docker logs erpnext-backend-1 --tail 100 -f
docker logs erpnext-frontend-1 --tail 100 -f

# 重启容器
docker restart erpnext-frontend-1
docker restart erpnext-backend-1

# 进入容器
docker exec -it erpnext-backend-1 bash
```

### 6.2 Frappe 命令

```bash
# 清除缓存
docker exec erpnext-backend-1 bench --site 172.16.200.44 clear-cache

# 迁移数据库
docker exec erpnext-backend-1 bench --site 172.16.200.44 migrate

# 重启服务
docker exec erpnext-backend-1 bench restart

# 查看站点列表
docker exec erpnext-backend-1 ls -la /home/frappe/frappe-bench/sites/
```

### 6.3 故障排查

```bash
# 测试本地访问
curl -I http://127.0.0.1:8085
curl -I http://172.16.200.44:8085

# 测试域名访问
curl -I https://psp.xajuzi.com

# 检查端口监听
ss -tlnp | grep 8085

# 查看后端错误日志
docker exec erpnext-backend-1 cat /home/frappe/frappe-bench/logs/bench-start.log
docker exec erpnext-backend-1 cat /home/frappe/frappe-bench/logs/web.error.log

# 检查核心静态资源与自定义应用 manifest
curl -I http://127.0.0.1:8085/assets/frappe/dist/css/desk.bundle.css || true
curl -I http://127.0.0.1:8085/assets/product_sales_planning/planning/manifest.json
```

## 7. 常见问题

### Q1: 502 Bad Gateway

**原因：** 网关无法连接到后端服务器

**排查：**
1. 检查容器是否运行：`docker ps | grep erpnext-frontend-1`
2. 检查端口是否监听：`ss -tlnp | grep 8085`
3. 检查网关到应用服务器的网络连通性

### Q2: 飞书登录报错"重定向 URL 有误"

**原因：** 飞书开放平台配置的回调地址与实际不符

**解决：**
1. 检查飞书开放平台的重定向 URL 配置
2. 确保完全匹配：`https://psp.xajuzi.com/api/method/...`
3. 检查 Frappe Social Login Key 配置

### Q3: 页面样式或资源加载失败

**原因：** 多数情况下不是域名本身有问题，而是静态资源清单与 `frontend` 实际文件不同步

**解决：**
```bash
# 先检查资源是否能返回 200
curl -I http://127.0.0.1:8085/assets/frappe/dist/css/desk.bundle.css || true
curl -I http://127.0.0.1:8085/assets/product_sales_planning/planning/manifest.json

# 再清除缓存
docker exec erpnext-backend-1 bench --site 172.16.200.44 clear-cache
docker exec erpnext-backend-1 bench --site 172.16.200.44 clear-website-cache
```

**重要警告：**

- 不要在生产环境只执行 `docker exec erpnext-backend-1 bench build`
- `sites/assets/assets.json` 是共享的，但 `frontend` 容器里的 `apps/.../public/dist` 不一定会一起更新
- 一旦单边 build，最常见结果就是 Desk CSS 404、页面错乱、自定义页面白屏

如果已经踩中这个坑，请直接参考 `docs/03-production/中文部署文档/04-ERPNext-CSS-404-排查与修复（容器资源不同步）.md`，按文档里的 `backend -> frontend` 资源同步步骤处理。

### Q4: WebSocket 连接失败

**原因：** 网关未正确代理 WebSocket

**解决：**
确保网关 nginx 配置包含 WebSocket 支持头：
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## 8. 配置文件清单

| 文件 | 位置 | 说明 |
|------|------|------|
| Docker Compose | `/root/gitops/erpnext-ip.yaml` | Docker 编排配置 |
| 环境变量 | `/root/gitops/erpnext.env` | 环境配置 |
| Nginx 配置 | `/usr/local/nginx/conf-file/psp.conf` | 网关反向代理 |
| Frappe 站点 | `sites/172.16.200.44/` | 站点配置目录 |

---

**文档版本：** 2026-03-18
**适用环境：** 生产环境域名访问
