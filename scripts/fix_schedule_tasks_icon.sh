#!/usr/bin/env bash
#
# fix_schedule_tasks_icon.sh
# ------------------------------------------------------------------
# 用途: 修复「计划任务 (Schedule Tasks)」在 Workspace 侧边栏图标不显示的问题。
#
# 根因:
#   Frappe v16 侧边栏渲染优先读取 tabWorkspace Link.icon。
#   发版(换镜像)后 bench migrate 不会同步该字段, 导致 icon IS NULL 而显示为空。
#
#   渲染链:
#     Workspace -> tabWorkspace Link.icon  (优先)
#                       |
#                       v (fallback)
#                 tabDocType.icon
#
# 本脚本做以下事情:
#   1. 检测 tabWorkspace Link 表是否存在 icon 列 (兼容未来版本)
#   2. 精确更新该 Workspace 下该条目的 icon  (parent + label + link_to 三条件)
#   3. 同步更新 tabDocType.icon (fallback 保障)
#   4. 清 Frappe 缓存 (clear-cache + clear-website-cache)
#   5. 重启 redis-cache (可选, RESTART_REDIS=1 启用)
#   6. 输出验证结果
#
# 用法:
#   chmod +x fix_schedule_tasks_icon.sh
#   ./fix_schedule_tasks_icon.sh
#
# 可选环境变量:
#   COMPOSE_FILE    compose 文件路径 (默认 /root/gitops/erpnext-ip.yaml)
#   SITE_NAME       Frappe 站点名     (默认 psp.xajuzi.com)
#   ICON_NAME       Feather icon 名   (默认 list)
#   WS_PARENT       Workspace 名称    (默认 产品销售规划)
#   WS_LABEL        链接显示名        (默认 计划任务)
#   RESTART_REDIS   设为 1 则重启 redis-cache (默认 0)
# ------------------------------------------------------------------
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/root/gitops/erpnext-ip.yaml}"
PROJECT_NAME="psp"
SITE_NAME="${SITE_NAME:-psp.xajuzi.com}"
ICON_NAME="${ICON_NAME:-list}"
WS_PARENT="${WS_PARENT:-产品销售规划}"
WS_LABEL="${WS_LABEL:-计划任务}"
RESTART_REDIS="${RESTART_REDIS:-0}"

DC="docker compose -p ${PROJECT_NAME} -f ${COMPOSE_FILE}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
info() { echo -e "  ${CYAN}->${NC} $1"; }

echo "=========================================="
echo "  修复 Workspace Link Schedule Tasks 图标"
echo "  站点:       ${SITE_NAME}"
echo "  图标:       ${ICON_NAME}"
echo "  Workspace:  ${WS_PARENT} -> ${WS_LABEL}"
echo "  compose:    ${COMPOSE_FILE}"
echo "=========================================="

# ---- 检查 backend 是否在线 ----
if ! ${DC} ps --services --filter "status=running" 2>/dev/null | grep -q '^backend$'; then
  fail "backend 容器未运行, 请先启动服务"
  exit 1
fi
ok "backend 容器运行中"

# --------------------------------------------------
# [1/5] 查看当前状态
# --------------------------------------------------
echo -e "\n[1/5] 查看当前 icon 状态..."
${DC} exec -T backend bash -lc "
  cd /home/frappe/frappe-bench
  bench --site '${SITE_NAME}' mariadb --execute \"
    SELECT name, icon FROM \\\`tabDocType\\\` WHERE name='Schedule Tasks';
    SELECT parent, label, link_to, icon
    FROM   \\\`tabWorkspace Link\\\`
    WHERE  parent   = '${WS_PARENT}'
    AND    label    = '${WS_LABEL}'
    AND    link_to  = 'Schedule Tasks';
  \"
" || warn "查询失败, 继续执行修复..."

# --------------------------------------------------
# [2/5] 检测 tabWorkspace Link 是否有 icon 列
# --------------------------------------------------
echo -e "\n[2/5] 检测 tabWorkspace Link 是否存在 icon 列..."
HAS_ICON_COL=$(${DC} exec -T backend bash -lc "
  cd /home/frappe/frappe-bench
  bench --site '${SITE_NAME}' mariadb --skip-column-names --silent --execute \"
    SELECT COUNT(*)
    FROM   information_schema.columns
    WHERE  table_schema = DATABASE()
    AND    table_name   = 'tabWorkspace Link'
    AND    column_name  = 'icon';
  \"
" 2>/dev/null | tr -d '[:space:]')

if [ "${HAS_ICON_COL}" = "1" ]; then
  ok "icon 列存在, 继续更新"
  SKIP_WS_UPDATE=0
else
  warn "tabWorkspace Link 不含 icon 列 (可能是旧版 Frappe), 跳过 Workspace Link 更新"
  SKIP_WS_UPDATE=1
fi

# --------------------------------------------------
# [3/5] 精确更新 tabWorkspace Link.icon
#        三条件: parent + label + link_to → 不会误伤其他 Workspace
# --------------------------------------------------
echo -e "\n[3/5] 更新 tabWorkspace Link icon -> '${ICON_NAME}'..."
if [ "${SKIP_WS_UPDATE}" = "0" ]; then
  ${DC} exec -T backend bash -lc "
    cd /home/frappe/frappe-bench
    bench --site '${SITE_NAME}' mariadb --execute \"
      SET SQL_SAFE_UPDATES = 0;
      UPDATE \\\`tabWorkspace Link\\\`
      SET    icon    = '${ICON_NAME}'
      WHERE  parent  = '${WS_PARENT}'
      AND    label   = '${WS_LABEL}'
      AND    link_to = 'Schedule Tasks';
      SELECT ROW_COUNT() AS ws_link_updated_rows;
      SET SQL_SAFE_UPDATES = 1;
    \"
  " && ok "tabWorkspace Link icon 已更新 (三条件精确匹配)" \
    || fail "tabWorkspace Link 更新失败"
else
  warn "[3/5] 已跳过 (icon 列不存在)"
fi

# --------------------------------------------------
# [4/5] 同步更新 tabDocType.icon (fallback 保障)
# --------------------------------------------------
echo -e "\n[4/5] 更新 tabDocType icon -> '${ICON_NAME}' (fallback)..."
${DC} exec -T backend bash -lc "
  cd /home/frappe/frappe-bench
  bench --site '${SITE_NAME}' mariadb --execute \"
    UPDATE \\\`tabDocType\\\`
    SET    icon = '${ICON_NAME}'
    WHERE  name = 'Schedule Tasks';
    SELECT ROW_COUNT() AS dt_updated_rows;
  \"
" && ok "tabDocType icon 已更新" || warn "tabDocType 更新失败 (非致命)"

# --------------------------------------------------
# [5/5] 清缓存
#   Workspace 数据走 frappe.boot / workspace_sidebar / module_page 缓存
#   必须全部清除, 否则页面刷新仍读旧数据
# --------------------------------------------------
echo -e "\n[5/5] 清缓存..."

${DC} exec -T backend bench --site "${SITE_NAME}" clear-cache \
  && ok "clear-cache 完成" || warn "clear-cache 失败"

${DC} exec -T backend bench --site "${SITE_NAME}" clear-website-cache 2>/dev/null \
  && ok "clear-website-cache 完成" || warn "clear-website-cache 不可用, 跳过"

# 可选: 重启 redis-cache 彻底清除残留
if [ "${RESTART_REDIS}" = "1" ]; then
  info "重启 redis-cache..."
  ${DC} restart redis-cache \
    && ok "redis-cache 已重启" || warn "redis-cache 重启失败"
else
  info "如页面刷新后仍显示旧数据, 可加 RESTART_REDIS=1 重跑以重启 redis-cache"
fi

# ---- 验证 ----
echo ""
echo "--- 验证结果 ---"
${DC} exec -T backend bash -lc "
  cd /home/frappe/frappe-bench
  bench --site '${SITE_NAME}' mariadb --execute \"
    SELECT name, icon FROM \\\`tabDocType\\\` WHERE name='Schedule Tasks';
    SELECT parent, label, link_to, icon
    FROM   \\\`tabWorkspace Link\\\`
    WHERE  parent   = '${WS_PARENT}'
    AND    label    = '${WS_LABEL}'
    AND    link_to  = 'Schedule Tasks';
  \"
"

echo ""
echo "=========================================="
echo "  修复完成!"
echo "  ★ 请在浏览器按 Ctrl+Shift+R 强制刷新"
echo ""
echo "  若图标仍不显示:"
echo "    1. 确认图标名: https://feathericons.com/"
echo "       常用: list / check-square / calendar / clipboard / task"
echo "    2. 重启 redis: RESTART_REDIS=1 ./fix_schedule_tasks_icon.sh"
echo "    3. 换图标名:   ICON_NAME=calendar ./fix_schedule_tasks_icon.sh"
echo ""
echo "  建议纳入 post-deploy 流程, 发版后自动执行无需手动补跑"
echo "=========================================="
