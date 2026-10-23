#!/usr/bin/env bash
# /root/gitops 目录清理脚本
# 用法: ./cleanup-gitops.sh          # 预览（dry-run，不实际删除）
#       ./cleanup-gitops.sh --run    # 实际执行删除
# ============================================================
set -euo pipefail

cd /root/gitops
DRY_RUN=1
[ "${1:-}" = "--run" ] && DRY_RUN=0

act() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "  [DRY-RUN] 将删除: $1"
  else
    rm -rf "$1" && echo "  [已删除] $1"
  fi
}

echo "=========================================="
if [ "$DRY_RUN" = "1" ]; then
  echo "  清理预览 (DRY-RUN, 不实际删除)"
  echo "  确认无误后用: $0 --run"
else
  echo "  正在执行清理"
fi
echo "=========================================="

# ---- 1. 空文件/空目录 ----
echo -e "\n[1/5] 空文件/空目录..."
act "erpnext-"
act "erpnext.yaml"
act "backups/"

# ---- 2. 废弃旧配置 ----
echo -e "\n[2/5] 废弃旧配置..."
act "erpnext.custom.env"
act "erpnext.domain.env"
act "erpnext.domain.yaml"
act "erpnext.env"
act "erpnext.ip.env"
act "erpnext.yaml.bak.20260409_142928"
act "Dockerfile.frappe-assets"

# ---- 3. 旧 compose 备份 (保留最新一个) ----
echo -e "\n[3/5] 旧 compose 备份 (保留最新)..."
act "erpnext-ip.yaml.bak.20260506162756"
act "erpnext-ip.yaml.bak.20260506173359"
act "erpnext-ip.yaml.bak.20260716174929"
# 保留 erpnext-ip.yaml.bak.20260727122105 (最新)

# ---- 4. 旧 assets 操作目录 ----
echo -e "\n[4/5] 旧 assets 操作目录..."
act "assets-backup-20260424-193110"
act "assets-fix-20260424-193810"
act "assets_from_image"
act "image_assets_manifest"

# ---- 5. 旧站点备份压缩包 (全是5月的, 约180MB) ----
echo -e "\n[5/5] 旧站点备份压缩包..."
act "erpnext_sites_backup_20260505130907.tar.gz"
act "erpnext_sites_before_assets_fix_20260505131304.tar.gz"
act "erpnext_sites_before_release_20260505134229.tar.gz"
act "erpnext_sites_before_release_20260506081653.tar.gz"
act "erpnext_sites_before_release_20260506082146.tar.gz"
act "erpnext_sites_before_release_20260507041807.tar.gz"
act "erpnext_sites_before_release_20260507042127.tar.gz"
act "erpnext_sites_before_v106_20260506082911.tar.gz"

# ---- 汇总 ----
echo -e "\n=========================================="
echo "  清理后保留的核心文件:"
echo "=========================================="
echo "  erpnext-ip.yaml              <- 生产 compose"
echo "  erpnext-ip.yaml.bak.20260727122105  <- 最新备份"
echo "  deploy-update.sh             <- 部署脚本"
echo "  apps.json                    <- 应用配置"
echo "  frappe_docker/               <- git 仓库"
if [ "$DRY_RUN" = "1" ]; then
  echo ""
  echo "  以上为预览, 确认后执行: $0 --run"
fi
echo ""
