<template>
  <div class="repository-config-page" id="repository-config-page">
    <!-- Page Header -->
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; gap: 16px; flex-wrap: wrap;">
      <div>
        <h2 style="font-size: 1.45rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 10px;">
          <span>Codeup 认证凭证与代码仓库</span>
          <span style="font-size: 0.76rem; font-weight: 600; padding: 2px 10px; border-radius: 9999px; background: #e0e7ff; color: #4338ca;">
            凭证已全面收敛
          </span>
        </h2>
        <p style="font-size: 0.88rem; color: var(--text-secondary); margin-top: 6px; max-width: 820px; line-height: 1.5;">
          全部 29 个代码库统一收敛至同一个云效组织（<code style="font-family: var(--font-mono); background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.82rem;">64c8b550dcc8d50d3cc7f5b4</code>），组织 ID 与访问令牌由<strong>研发工作台设置</strong>全局维护与继承，单库支持特定覆盖配置与自定义排除规则，内置到期自动预警。
        </p>
      </div>

      <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
        <button
          type="button"
          class="btn-secondary"
          :disabled="isConverging"
          @click="handleConvergeCredentials"
          title="将所有单库冗余凭证清空，全部无缝继承全局设置"
          style="display: flex; align-items: center; gap: 6px;"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>{{ isConverging ? '收敛处理中...' : '一键收敛凭证至全局' }}</span>
        </button>

        <a
          href="/app/dev-workbench-settings"
          target="_blank"
          class="btn-secondary"
          style="display: flex; align-items: center; gap: 6px;"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          Desk 系统设置
        </a>

        <a
          href="/app/codeup-repository/new"
          target="_blank"
          class="btn-primary"
          style="display: flex; align-items: center; gap: 6px;"
        >
          <span>+ 添加代码库</span>
        </a>
      </div>
    </div>

    <!-- Alert / Expiry Notification Banner -->
    <div
      v-if="summary.need_attention"
      style="margin-bottom: 20px; padding: 14px 20px; border-radius: var(--radius-md); background: #fef2f2; border: 1px solid #fecaca; display: flex; align-items: center; justify-content: space-between; gap: 16px;"
    >
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 1.25rem;">⚠️</span>
        <div>
          <div style="font-weight: 700; color: #b91c1c; font-size: 0.92rem;">
            Codeup 访问令牌即将到期或已过期！
          </div>
          <div style="font-size: 0.82rem; color: #991b1b; margin-top: 2px;">
            当前令牌到期时间为 {{ summary.global_expires_at }}（剩余 {{ summary.days_left }} 天），请尽快更新以保障同步定时任务正常进行。
          </div>
        </div>
      </div>
      <button type="button" class="btn-primary" style="background: #dc2626; border-color: #dc2626; font-size: 0.82rem; padding: 6px 14px;" @click="showEditModal = true">
        立即更新令牌
      </button>
    </div>

    <!-- Global Credentials Card -->
    <div style="background: #ffffff; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); padding: 22px 24px; margin-bottom: 28px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 34px; height: 34px; border-radius: 8px; background: #eef2ff; color: #4f46e5; display: flex; align-items: center; justify-content: center;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
          </div>
          <div>
            <h3 style="font-size: 1.08rem; font-weight: 700; color: var(--text-primary);">
              研发工作台全局 Codeup 认证配置
            </h3>
            <span style="font-size: 0.78rem; color: var(--text-muted);">
              单例模型 (Dev Workbench Settings) · 统一凭证与安全加密存储
            </span>
          </div>
        </div>

        <div style="display: flex; gap: 8px; align-items: center;">
          <button
            type="button"
            class="btn-secondary"
            style="padding: 6px 14px; font-size: 0.82rem;"
            @click="showEditModal = !showEditModal"
          >
            {{ showEditModal ? '收起编辑表单' : '编辑全局配置' }}
          </button>
          <button
            type="button"
            class="btn-secondary"
            style="padding: 6px 12px; font-size: 0.82rem;"
            @click="refreshData"
            title="重新拉取配置与令牌状态"
          >
            🔄 刷新状态
          </button>
        </div>
      </div>

      <!-- Quick Metrics Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px; margin-bottom: 8px;">
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius-md); padding: 14px 16px;">
          <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 6px;">全局云效组织 ID</div>
          <div style="font-family: var(--font-mono); font-size: 0.88rem; font-weight: 600; color: var(--text-primary); word-break: break-all;">
            {{ globalConfig.codeup_organization_id || '未配置' }}
          </div>
          <div style="font-size: 0.75rem; color: #10b981; margin-top: 4px;">✓ 默认主组织</div>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius-md); padding: 14px 16px;">
          <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 6px;">全局个人访问令牌</div>
          <div style="font-family: var(--font-mono); font-size: 0.88rem; font-weight: 600; color: var(--text-primary);">
            {{ globalConfig.codeup_access_token_masked || (globalConfig.has_access_token ? '已配置 (已脱敏)' : '未设置') }}
          </div>
          <div style="font-size: 0.75rem; color: #6366f1; margin-top: 4px;">✓ Frappe Password 密文存储</div>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius-md); padding: 14px 16px;">
          <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 6px;">令牌到期时间与状态</div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-family: var(--font-mono); font-size: 0.88rem; font-weight: 600; color: var(--text-primary);">
              {{ globalConfig.codeup_token_expires_at || '未设置' }}
            </span>
            <span
              v-if="summary.global_status === 'valid'"
              style="padding: 2px 7px; border-radius: 9999px; font-size: 0.72rem; font-weight: 600; background: #ecfdf5; color: #047857;"
            >
              正常 (剩余 {{ summary.days_left }} 天)
            </span>
            <span
              v-else-if="summary.global_status === 'expiring_soon'"
              style="padding: 2px 7px; border-radius: 9999px; font-size: 0.72rem; font-weight: 600; background: #fffbeb; color: #b45309;"
            >
              临期 (仅剩 {{ summary.days_left }} 天)
            </span>
            <span
              v-else-if="summary.global_status === 'expired'"
              style="padding: 2px 7px; border-radius: 9999px; font-size: 0.72rem; font-weight: 600; background: #fef2f2; color: #b91c1c;"
            >
              已过期
            </span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
            提前 {{ globalConfig.codeup_token_alert_days || 7 }} 天自动向管理者发送预警
          </div>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius-md); padding: 14px 16px;">
          <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 6px;">代码库凭证收敛分布</div>
          <div style="display: flex; align-items: baseline; gap: 6px;">
            <span style="font-size: 1.15rem; font-weight: 700; color: #047857;">{{ summary.inherited_count }}</span>
            <span style="font-size: 0.8rem; color: var(--text-secondary);">继承全局</span>
            <span style="color: #cbd5e1;">/</span>
            <span style="font-size: 1.15rem; font-weight: 700; color: #b45309;">{{ summary.override_count }}</span>
            <span style="font-size: 0.8rem; color: var(--text-secondary);">独立覆盖</span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
            全组织共 {{ summary.total_repositories }} 个代码库
          </div>
        </div>
      </div>

      <!-- Inline Edit Form (Toggled) -->
      <div v-if="showEditModal" style="margin-top: 20px; padding: 20px; background: #f8fafc; border-radius: var(--radius-md); border: 1px solid #e2e8f0;">
        <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 14px; color: var(--text-primary);">
          编辑全局 Codeup 配置
        </h4>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 16px;">
          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 600; margin-bottom: 6px; color: var(--text-secondary);">
              云效组织 ID (Organization ID) *
            </label>
            <input
              v-model="editForm.codeup_organization_id"
              type="text"
              class="form-control"
              style="width: 100%; padding: 8px 12px; font-size: 0.88rem; border-radius: var(--radius-sm); border: 1px solid var(--border-medium); font-family: var(--font-mono);"
              placeholder="例如: 64c8b550dcc8d50d3cc7f5b4"
            />
          </div>

          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 600; margin-bottom: 6px; color: var(--text-secondary);">
              个人访问令牌 (Personal Access Token)
            </label>
            <input
              v-model="editForm.codeup_access_token"
              type="password"
              class="form-control"
              style="width: 100%; padding: 8px 12px; font-size: 0.88rem; border-radius: var(--radius-sm); border: 1px solid var(--border-medium); font-family: var(--font-mono);"
              placeholder="留空则保持现有令牌不变"
            />
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
              当前已配置: {{ globalConfig.codeup_access_token_masked || '未配置' }}
            </div>
          </div>

          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 600; margin-bottom: 6px; color: var(--text-secondary);">
              令牌到期日期 (Token Expires At)
            </label>
            <input
              v-model="editForm.codeup_token_expires_at"
              type="date"
              class="form-control"
              style="width: 100%; padding: 8px 12px; font-size: 0.88rem; border-radius: var(--radius-sm); border: 1px solid var(--border-medium);"
            />
          </div>

          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 600; margin-bottom: 6px; color: var(--text-secondary);">
              提前预警天数 (Alert Days)
            </label>
            <input
              v-model.number="editForm.codeup_token_alert_days"
              type="number"
              min="1"
              max="90"
              class="form-control"
              style="width: 100%; padding: 8px 12px; font-size: 0.88rem; border-radius: var(--radius-sm); border: 1px solid var(--border-medium);"
            />
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button type="button" class="btn-secondary" @click="showEditModal = false">
            取消
          </button>
          <button type="button" class="btn-primary" :disabled="isSaving" @click="handleSaveGlobalConfig">
            {{ isSaving ? '保存中...' : '保存全局凭证设置' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Repositories List Table -->
    <div style="background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 18px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <h3 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">
            代码库凭证与配置列表 ({{ filteredRepos.length }} / {{ repos.length }})
          </h3>
          <span style="font-size: 0.78rem; padding: 2px 8px; border-radius: 9999px; background: #ecfdf5; color: #047857;">
            {{ summary.inherited_count }} 个自动继承
          </span>
        </div>

        <!-- Filter & Search Controls -->
        <div style="display: flex; gap: 10px; align-items: center;">
          <select
            v-model="filterMode"
            style="padding: 6px 12px; font-size: 0.84rem; border-radius: var(--radius-sm); border: 1px solid var(--border-medium); background: #ffffff;"
          >
            <option value="all">全部凭证模式</option>
            <option value="inherited">仅全局继承 ({{ summary.inherited_count }})</option>
            <option value="override">仅单库覆盖 ({{ summary.override_count }})</option>
          </select>

          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索代码库名称或 ID..."
            style="padding: 6px 12px; font-size: 0.84rem; border-radius: var(--radius-sm); border: 1px solid var(--border-medium); width: 220px;"
          />
        </div>
      </div>

      <div v-if="filteredRepos.length === 0" style="padding: 48px; text-align: center; color: var(--text-muted);">
        未找到匹配的代码库配置
      </div>

      <div v-else style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 0.82rem;">
              <th style="padding: 12px 24px;">代码库名称</th>
              <th style="padding: 12px 16px;">代码库 ID</th>
              <th style="padding: 12px 16px;">凭证模式</th>
              <th style="padding: 12px 16px;">生效组织 ID</th>
              <th style="padding: 12px 16px;">默认分支</th>
              <th style="padding: 12px 16px;">启用状态</th>
              <th style="padding: 12px 24px; text-align: right;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredRepos" :key="r.name" style="border-bottom: 1px solid #f1f5f9; transition: background 150ms ease;" class="repo-row">
              <td style="padding: 14px 24px;">
                <div style="font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                  <span>{{ r.repository_name || r.name }}</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">
                  Doc: {{ r.name }}
                </div>
              </td>

              <td style="padding: 14px 16px; font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-secondary);">
                {{ r.repo_id }}
              </td>

              <td style="padding: 14px 16px;">
                <span
						v-if="!r.has_access_token && (!r.org_id || r.org_id === globalConfig.codeup_organization_id)"
                  style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; background: #ecfdf5; color: #047857;"
                >
                  <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
                  全局继承
                </span>
                <span
                  v-else
                  style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; background: #fffbeb; color: #b45309;"
                >
                  <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #f59e0b;"></span>
                  单库覆盖
                </span>
              </td>

              <td style="padding: 14px 16px; font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-secondary);">
                <span>{{ r.org_id || globalConfig.codeup_organization_id || '-' }}</span>
                <span v-if="!r.org_id" style="font-size: 0.72rem; color: var(--text-muted); margin-left: 4px;">(继承)</span>
              </td>

              <td style="padding: 14px 16px; font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-secondary);">
                {{ r.default_branch || 'master' }}
              </td>

              <td style="padding: 14px 16px;">
                <span v-if="r.is_active" style="background: #ecfdf5; color: #047857; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem;">启用中</span>
                <span v-else style="background: #f1f5f9; color: #94a3b8; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem;">已禁用</span>
              </td>

              <td style="padding: 14px 24px; text-align: right;">
                <a :href="`/app/codeup-repository/${r.name}`" target="_blank" class="btn-secondary" style="padding: 4px 10px; font-size: 0.78rem;">
                  在 Desk 中配置特定覆盖
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Toast Notification -->
    <div v-if="toastMessage" class="toast-bar" style="position: fixed; bottom: 28px; right: 28px; background: #0f172a; color: #fff; padding: 12px 20px; border-radius: 10px; font-size: 0.88rem; box-shadow: var(--shadow-lg); display: flex; align-items: center; gap: 10px; z-index: 9999;">
      <span>{{ toastMessage }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { request, api } from '@/utils/api'

const repos = ref([])
const searchQuery = ref('')
const filterMode = ref('all')
const isConverging = ref(false)
const isSaving = ref(false)
const showEditModal = ref(false)
const toastMessage = ref('')

const globalConfig = ref({
  codeup_organization_id: '64c8b550dcc8d50d3cc7f5b4',
  codeup_base_url: 'https://codeup.aliyun.com',
  codeup_token_expires_at: '',
  codeup_token_alert_days: 7,
  codeup_access_token_masked: '',
  has_access_token: false,
})

const summary = ref({
  global_status: 'valid',
  global_expires_at: '',
  days_left: null,
  alert_days: 7,
  total_repositories: 29,
  inherited_count: 29,
  override_count: 0,
  need_attention: false,
})

const editForm = ref({
  codeup_organization_id: '',
  codeup_access_token: '',
  codeup_token_expires_at: '',
  codeup_token_alert_days: 7,
})

const showToast = (msg) => {
  toastMessage.value = msg
  setTimeout(() => {
    toastMessage.value = ''
  }, 3500)
}

const fetchGlobalConfig = async () => {
  try {
    const res = await api.get('/api/method/dev_workbench.api.v1.settings.get_codeup_config')
    const json = await res.json()
    const data = json.message || json
    if (data && data.codeup_organization_id) {
      globalConfig.value = {
        codeup_organization_id: data.codeup_organization_id,
        codeup_base_url: data.codeup_base_url,
        codeup_token_expires_at: data.codeup_token_expires_at,
        codeup_token_alert_days: data.codeup_token_alert_days,
        codeup_access_token_masked: data.codeup_access_token_masked,
        has_access_token: data.has_access_token,
      }
      if (data.summary) {
        summary.value = data.summary
      }

      // 预填编辑表单
      editForm.value.codeup_organization_id = data.codeup_organization_id
      editForm.value.codeup_token_expires_at = data.codeup_token_expires_at
      editForm.value.codeup_token_alert_days = data.codeup_token_alert_days
      editForm.value.codeup_access_token = ''
    }
  } catch (err) {
    console.error('获取 Codeup 全局配置失败:', err)
  }
}

const fetchRepositories = async () => {
  try {
		const res = await request('/api/method/dev_workbench.api.v1.settings.get_codeup_repositories')
    const data = await res.json()
		repos.value = data.message || []
  } catch (err) {
    console.error('获取代码库列表失败:', err)
  }
}

const refreshData = async () => {
  await Promise.all([fetchGlobalConfig(), fetchRepositories()])
  showToast('配置与令牌状态已刷新')
}

const handleSaveGlobalConfig = async () => {
  if (!editForm.value.codeup_organization_id) {
    alert('请填写云效组织 ID')
    return
  }
  isSaving.value = true
  try {
		await api.post('/api/method/dev_workbench.api.v1.settings.save_codeup_config', editForm.value)
    showToast('Codeup 全局凭证配置已保存成功！')
    showEditModal.value = false
    await refreshData()
  } catch (err) {
    alert('保存全局配置失败: ' + err.message)
  } finally {
    isSaving.value = false
  }
}

const handleConvergeCredentials = async () => {
  if (!confirm('确定要将现有全部代码库凭证收敛至全局吗？\n这将清空单库冗余的 access_token 与匹配组织 ID，全面统一继承。')) {
    return
  }
  isConverging.value = true
  try {
		const res = await api.post('/api/method/dev_workbench.api.v1.settings.converge_repo_credentials')
    const json = await res.json()
    const msg = json.message || json
    showToast(typeof msg === 'string' ? msg : '已收敛代码库凭证至全局设置')
    await refreshData()
  } catch (err) {
    alert('收敛凭证失败: ' + err.message)
  } finally {
    isConverging.value = false
  }
}

const filteredRepos = computed(() => {
  return repos.value.filter(r => {
    // 搜索过滤
    const q = searchQuery.value.trim().toLowerCase()
    const nameMatch = !q || (r.repository_name || '').toLowerCase().includes(q) || r.name.toLowerCase().includes(q) || (r.repo_id || '').toLowerCase().includes(q)
    if (!nameMatch) return false

    // 模式过滤
		const isInherited = !r.has_access_token && (!r.org_id || r.org_id === globalConfig.value.codeup_organization_id)
    if (filterMode.value === 'inherited') return isInherited
    if (filterMode.value === 'override') return !isInherited
    return true
  })
})

onMounted(() => {
  fetchGlobalConfig()
  fetchRepositories()
})
</script>

<style scoped>
.repo-row:hover {
  background: #f8fafc;
}
</style>
