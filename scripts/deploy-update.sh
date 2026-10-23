#!/usr/bin/env bash
#
# PSP 服务器部署脚本
# ------------------------------------------------------------------
# 用途: 在服务器上更新 PSP 镜像版本 -- 备份、换 tag、拉镜像、重建容器、迁移、验证。
#       对应 compose 文件 erpnext-ip.yaml (project name: psp)。
# 服务器: 172.16.200.44, compose 文件放 /root/gitops/ 下。
#
# 用法:
#   ./deploy-update.sh <新镜像tag>
#   示例: ./deploy-update.sh v1.1.1
#
# 回滚: 用旧 tag 再跑一次本脚本即可。
#   ./deploy-update.sh v1.0.8
#
# 可选环境变量:
#   COMPOSE_FILE  compose 文件路径 (默认 /root/gitops/erpnext-ip.yaml)
#   SKIP_BACKUP=1 跳过备份 (紧急回滚时用)
#   SKIP_MIGRATE=1 跳过 migrate (仅换镜像时用)
# ------------------------------------------------------------------
set -euo pipefail

# ==================== 配置 ====================
COMPOSE_FILE="${COMPOSE_FILE:-/root/gitops/erpnext-ip.yaml}"
PROJECT_NAME="psp"
SITE_NAME="psp.xajuzi.com"
REGISTRY="crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723"
IMAGE="${REGISTRY}/frappev16"
FRONTEND_PORT="8085"
# 验证用文件 (md5 对比 develop)
VERIFY_FILE="product_sales_planning/product_sales_planning/planning_system/doctype/tasks_store/tasks_store.json"
# ===============================================

NEW_TAG="${1:-}"
DC="docker compose -p ${PROJECT_NAME} -f ${COMPOSE_FILE}"

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
info() { echo -e "  ${CYAN}->${NC} $1"; }

usage() {
  echo "用法: $0 <新镜像tag>"
  echo "示例: $0 v1.1.1"
  echo "回滚: $0 v1.0.8   # 用旧 tag 重跑即可"
  echo ""
  echo "可选环境变量:"
  echo "  COMPOSE_FILE=...   指定 compose 文件路径"
  echo "  SKIP_BACKUP=1      跳过备份"
  echo "  SKIP_MIGRATE=1     跳过 migrate"
  exit 1
}

[ -z "$NEW_TAG" ] && usage
[ ! -f "$COMPOSE_FILE" ] && { echo "✗ 找不到 compose 文件: $COMPOSE_FILE"; echo "  用 COMPOSE_FILE=... 覆盖"; exit 1; }

echo "=========================================="
echo "  PSP 部署更新"
echo "  镜像:     ${IMAGE}:${NEW_TAG}"
echo "  站点:     ${SITE_NAME}"
echo "  compose:  ${COMPOSE_FILE}"
echo "=========================================="

# --------------------------------------------------
# [1/7] 备份
# --------------------------------------------------
echo -e "\n[1/7] 备份数据..."
if [ "${SKIP_BACKUP:-0}" = "1" ]; then
  warn "已跳过备份 (SKIP_BACKUP=1)"
elif ${DC} ps --services --filter "status=running" 2>/dev/null | grep -q '^backend$'; then
  if ${DC} exec -T backend bench --site "${SITE_NAME}" backup --with-files; then
    ok "备份完成"
  else
    fail "备份失败, 已终止 (数据未动, 可排查后重试)"
    exit 1
  fi
else
  warn "backend 未运行, 跳过备份 (首次部署?)"
fi

# --------------------------------------------------
# [2/7] 替换 compose 镜像 tag (全局替换所有 frappev16:<旧tag>)
# --------------------------------------------------
echo -e "\n[2/7] 更新 compose 镜像 tag -> ${NEW_TAG}..."
BACKUP_TS=$(date +%Y%m%d%H%M%S)
cp "${COMPOSE_FILE}" "${COMPOSE_FILE}.bak.${BACKUP_TS}"
sed -i -E "s|${IMAGE}:[a-zA-Z0-9._-]+|${IMAGE}:${NEW_TAG}|g" "${COMPOSE_FILE}"

# 确认替换结果
REMAIN=$(grep -c "frappev16:v[0-9]" "${COMPOSE_FILE}" || true)
TOTAL=$(grep -c "frappev16:" "${COMPOSE_FILE}" || true)
NEW_COUNT=$(grep -c "frappev16:${NEW_TAG}" "${COMPOSE_FILE}" || true)
if [ "$NEW_COUNT" != "$TOTAL" ]; then
  fail "替换不完整: ${NEW_COUNT}/${TOTAL} 处为新 tag, 可能有残留"
  grep 'frappev16:' "${COMPOSE_FILE}"
  echo "  旧文件备份: ${COMPOSE_FILE}.bak.${BACKUP_TS}"
  exit 1
fi
ok "已替换 ${NEW_COUNT} 处 (旧文件备份: ${COMPOSE_FILE}.bak.${BACKUP_TS})"

# --------------------------------------------------
# [3/7] 拉取新镜像
# --------------------------------------------------
echo -e "\n[3/7] 拉取新镜像..."
if ${DC} pull; then
  ok "拉取完成"
else
  fail "拉取失败, 请检查网络/登录状态"
  echo "  尝试: docker login --username=15309154328 ${REGISTRY}"
  exit 1
fi

# --------------------------------------------------
# [4/7] 重建容器
# --------------------------------------------------
echo -e "\n[4/7] 重建容器..."
${DC} up -d
ok "容器已启动"

# --------------------------------------------------
# [5/7] 等待 backend 就绪
# --------------------------------------------------
echo -e "\n[5/7] 等待 backend 就绪..."
ready=0
for i in $(seq 1 60); do
  if ${DC} exec -T backend bash -lc "bench --site ${SITE_NAME} list-apps >/dev/null 2>&1"; then
    ready=1; break
  fi
  echo -ne "  等待中... ($i/60)\r"
  sleep 2
done
echo ""
if [ "$ready" != "1" ]; then
  fail "backend 120s 内未就绪"
  echo "  查日志: ${DC} logs --tail=50 backend"
  exit 1
fi
ok "backend 就绪"

# --------------------------------------------------
# [6/7] 迁移 + 清缓存
# --------------------------------------------------
echo -e "\n[6/7] 迁移 + 清缓存..."
if [ "${SKIP_MIGRATE:-0}" = "1" ]; then
  warn "已跳过 migrate (SKIP_MIGRATE=1)"
else
  ${DC} exec -T backend bench --site "${SITE_NAME}" migrate
  ok "migrate 完成"
fi
${DC} exec -T backend bench --site "${SITE_NAME}" clear-cache
ok "clear-cache 完成"

# --------------------------------------------------
# [7/7] 验证
# --------------------------------------------------
echo -e "\n[7/7] 验证..."
echo ""

# ① 容器状态
${DC} ps

# ② 代码 md5
echo ""
echo "--- 代码 md5 (应等于 develop 上的值) ---"
${DC} exec -T backend bash -lc "md5sum /home/frappe/frappe-bench/apps/${VERIFY_FILE}" 2>/dev/null || warn "验证文件不存在"

# ③ desk.bundle CSS 哈希对比 (防资源错位)
echo ""
echo "--- desk.bundle CSS 哈希对比 (backend 和 frontend 必须一致) ---"
BACKEND_CSS=$(${DC} exec -T backend  sh -lc 'ls /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css 2>/dev/null | grep desk.bundle || echo "NOT_FOUND"')
FRONTEND_CSS=$(${DC} exec -T frontend sh -lc 'ls /home/frappe/frappe-bench/apps/frappe/frappe/public/dist/css 2>/dev/null | grep desk.bundle || echo "NOT_FOUND"')
echo "  backend:  ${BACKEND_CSS}"
echo "  frontend: ${FRONTEND_CSS}"
if [ "$BACKEND_CSS" = "$FRONTEND_CSS" ] && [ "$BACKEND_CSS" != "NOT_FOUND" ]; then
  ok "CSS 哈希一致"
else
  warn "CSS 哈希不一致! 资源错位, 需修复:"
  echo "    ${DC} up -d --force-recreate backend"
  echo "    ${DC} exec backend bash -lc 'bench --site ${SITE_NAME} clear-cache && clear-website-cache'"
  echo "    ${DC} restart frontend"
fi

# ④ HTTP 可达
echo ""
echo "--- HTTP 可达性 ---"
if curl -sI "http://127.0.0.1:${FRONTEND_PORT}" | grep -q 'HTTP'; then
  ok "本地 ${FRONTEND_PORT} 端口可达"
else
  fail "本地 ${FRONTEND_PORT} 端口不可达"
fi
if curl -sI "https://${SITE_NAME}" | grep -q 'HTTP'; then
  ok "https://${SITE_NAME} 可达"
else
  warn "https://${SITE_NAME} 不可达 (可能需要等待 nginx/证书)"
fi

# --------------------------------------------------
echo ""
echo "=========================================="
echo "  部署完成: ${IMAGE}:${NEW_TAG}"
echo "=========================================="
echo ""
echo "常用命令:"
echo "  查看日志:   ${DC} logs -f backend"
echo "  查看状态:   ${DC} ps"
echo "  回滚:       $0 <旧tag>"
