#!/usr/bin/env bash
#
# 只更新 frappe 框架的镜像构建脚本
# ------------------------------------------------------------------
# 用途:重新构建镜像,拉取 version-16 分支最新 frappe。
#       product_sales_planning 是否更新,取决于其 main 分支自上次构建后有无新提交
#       (apps.json 里 psp 用的是 branch: main 滚动引用)。
# 环境:WSL Ubuntu-24.04(docker 装在这里,不是 Windows PowerShell)。
# 用法:
#   wsl -d Ubuntu-24.04
#   bash /mnt/d/project/02-开源项目/frappe_docker/scripts/update-frappe-only.sh
# ------------------------------------------------------------------
set -euo pipefail

# ==================== 配置 ====================
SRC="/mnt/d/project/02-开源项目/frappe_docker"
BUILD_DIR="/home/frappe/frappe_docker_build"
REGISTRY="crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723"
TMP_TAG="tmp-frappe-update"
# ===============================================

echo "============================================"
echo "  只更新 frappe 框架 - 镜像构建"
echo "============================================"

# 0. 前置检查:基础镜像必须存在
echo "[0/4] 检查基础镜像..."
for img in frappe/build:version-16 frappe/base:version-16; do
  if ! docker image inspect "$img" >/dev/null 2>&1; then
    echo "  ✗ 缺少基础镜像: $img"
    echo "    需先构建 base/build 镜像(见 frappe_docker 的 docker-bake.hcl)"
    exit 1
  fi
  echo "  ✓ $img"
done

# 1. 准备干净构建 context
#    只复制 images/ resources/ apps.json,避开 development/ 下的 1.2G venv
echo "[1/4] 准备构建目录: $BUILD_DIR"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cp -r "$SRC/images"    "$BUILD_DIR"/
cp -r "$SRC/resources" "$BUILD_DIR"/
cp    "$SRC/apps.json" "$BUILD_DIR"/
# 修复 Windows CRLF 换行符:git autocrlf 会让 .sh 变 CRLF,
# 容器内执行 entrypoint 会报 "exec entrypoint.sh: no such file or directory"
sed -i 's/\r$//' "$BUILD_DIR"/resources/core/*.sh
cd "$BUILD_DIR"

# 2. 构建镜像
#    - 新版 Containerfile 用 --secret 注入 apps.json(不再用 APPS_JSON_BASE64)
#    - CACHE_BUST 强制刷新 frappe 层,拉取 version-16 最新代码
echo "[2/4] 构建镜像..."
CACHE_BUST="$(date +%s)"

# --network=host:容器共享宿主网络,使容器内 127.0.0.1:7897 指向宿主 clash 代理。
# 但网络可达还不够 —— BuildKit **不会**继承宿主的 http_proxy/https_proxy 环境变量
# (实测:不加 --build-arg 时容器内 env 里没有任何代理变量)。而 github.com 直连被墙:
#     宿主直连 github   -> FAILED
#     宿主走 7897 代理  -> 200 (1.9s)
# 所以必须显式把代理以 --build-arg 传进去。否则 bench init 的
# `git ls-remote https://github.com/frappe/frappe` 会卡 134s 后超时,报
# InvalidRemoteException: Invalid frappe path;偶尔表现为
# `GnuTLS recv error (-110): The TLS connection was non-properly terminated`。
# docker 的预定义代理参数只作用于构建期,不会写进最终镜像配置。
PROXY_URL="${BUILD_PROXY:-http://127.0.0.1:7897}"
echo "  构建代理: ${PROXY_URL} (可用 BUILD_PROXY 环境变量覆盖)"

docker build \
  --network=host \
  --build-arg "HTTP_PROXY=${PROXY_URL}" \
  --build-arg "HTTPS_PROXY=${PROXY_URL}" \
  --build-arg "NO_PROXY=localhost,127.0.0.1,::1" \
  --secret=id=apps_json,src=apps.json \
  --build-arg=CACHE_BUST="${CACHE_BUST}" \
  --tag="${REGISTRY}/frappev16:${TMP_TAG}" \
  --file=images/layered/Containerfile .

# 3. 验证镜像内容
echo "[3/4] 验证镜像..."
echo "--- apps 列表 + 版本(确认 product_sales_planning 已注入、frappe 版本)---"
docker run --rm --entrypoint=bash "${REGISTRY}/frappev16:${TMP_TAG}" \
  -lc 'cd /home/frappe/frappe-bench && bench version'

echo "--- apps 目录 ---"
docker run --rm --entrypoint=bash "${REGISTRY}/frappev16:${TMP_TAG}" \
  -lc 'ls /home/frappe/frappe-bench/apps/'

# 4. 提示下一步
echo "[4/4] 构建完成。确认 bench version 输出无误后,打 tag 并推送:"
cat <<EOF

  # 设置最终 tag(延续 v1.0.x 序列,下一个建议 v1.0.9)
  FINAL_TAG=v1.0.9

  docker tag  ${REGISTRY}/frappev16:${TMP_TAG} ${REGISTRY}/frappev16:\${FINAL_TAG}
  docker login --username=15309154328 ${REGISTRY}
  docker push ${REGISTRY}/frappev16:\${FINAL_TAG}

  # 然后在服务器部署 + 迁移:
  ssh root@172.16.200.44
  /root/gitops/deploy-update.sh \${FINAL_TAG}

EOF
echo "提示:临时镜像 ${REGISTRY}/frappev16:${TMP_TAG} 推送后可用 docker rmi 清理。"
