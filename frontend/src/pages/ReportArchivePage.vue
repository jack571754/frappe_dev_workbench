<template>
  <div class="report-archive-page" id="report-archive-page">
    <!-- Top Metric Overview Grid -->
    <div class="metric-grid">
      <div class="metric-card" id="metric-card-total-reports">
        <div>
          <div class="metric-label">已归档日报总期数</div>
          <div class="metric-value">{{ reportsList.length }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">期</span></div>
        </div>
        <div class="metric-icon indigo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="21 8 21 21 3 21 3 8"></polyline>
            <rect x="1" y="3" width="22" height="5"></rect>
            <line x1="10" y1="12" x2="14" y2="12"></line>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-sent-reports">
        <div>
          <div class="metric-label">飞书成功推送</div>
          <div class="metric-value" style="color: #059669;">{{ sentCount }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">期</span></div>
        </div>
        <div class="metric-icon emerald">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-failed-reports">
        <div>
          <div class="metric-label">推送失败 / 草稿</div>
          <div class="metric-value" :style="{ color: failedOrDraftCount > 0 ? '#dc2626' : 'var(--text-secondary)' }">
            {{ failedOrDraftCount }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">期</span>
          </div>
        </div>
        <div class="metric-icon" :class="failedOrDraftCount > 0 ? 'rose' : 'amber'">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-latest-date">
        <div>
          <div class="metric-label">最新推送工作日</div>
          <div class="metric-value" style="font-size: 1.15rem; margin-top: 4px;">
            {{ latestReportDate || '暂无数据' }}
          </div>
        </div>
        <div class="metric-icon purple">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
          </svg>
        </div>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filter-panel" style="background: #fff; padding: 16px 20px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); margin-bottom: 20px;">
      <div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px;">
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 14px;">
          <!-- Date Range Filter -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">日期范围：</label>
            <input
              id="filter-report-from-date"
              type="date"
              v-model="fromDate"
              @change="fetchReports"
              class="form-input-sm"
            />
            <span style="color: var(--text-muted); font-size: 0.85rem;">至</span>
            <input
              id="filter-report-to-date"
              type="date"
              v-model="toDate"
              @change="fetchReports"
              class="form-input-sm"
            />
            <button type="button" class="btn-chip" :class="{ active: currentQuickRange === '1w' }" @click="setQuickRange('1w')">近 1 周</button>
            <button type="button" class="btn-chip" :class="{ active: currentQuickRange === '2w' }" @click="setQuickRange('2w')">近 2 周</button>
            <button type="button" class="btn-chip" :class="{ active: currentQuickRange === '4w' }" @click="setQuickRange('4w')">近 4 周</button>
            <button type="button" class="btn-chip" :class="{ active: currentQuickRange === 'all' }" @click="setQuickRange('all')">全部</button>
          </div>

          <!-- Status Filter -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">状态：</label>
            <select
              id="filter-report-status"
              v-model="statusFilter"
              class="form-input-sm"
              style="min-width: 110px;"
            >
              <option value="all">全部状态</option>
              <option value="Sent">已发送 (Sent)</option>
              <option value="Draft">草稿 (Draft)</option>
              <option value="Failed">失败 (Failed)</option>
              <option value="Recalled">已撤回 (Recalled)</option>
            </select>
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 12px;">
          <button
            type="button"
            id="btn-refresh-reports"
            class="btn-secondary-sm"
            @click="fetchReports"
            :disabled="loading"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ 'spin-anim': loading }">
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            刷新列表
          </button>
        </div>
      </div>
    </div>

    <!-- Alert / Toast Banner -->
    <div v-if="toastMessage" :class="['alert-banner', toastType === 'error' ? 'alert-danger' : 'alert-success']" style="margin-bottom: 16px;">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle v-if="toastType !== 'error'" cx="12" cy="12" r="10"></circle>
        <path v-if="toastType !== 'error'" d="M9 12l2 2 4-4"></path>
        <circle v-if="toastType === 'error'" cx="12" cy="12" r="10"></circle>
        <line v-if="toastType === 'error'" x1="12" y1="8" x2="12" y2="12"></line>
        <line v-if="toastType === 'error'" x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <span>{{ toastMessage }}</span>
      <button type="button" @click="toastMessage = ''" style="margin-left: auto; background: none; border: none; cursor: pointer; color: inherit;">×</button>
    </div>

    <!-- Report List Table Card -->
    <div class="content-card" style="background: #fff; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;">
        <h3 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="21 8 21 21 3 21 3 8"></polyline>
            <rect x="1" y="3" width="22" height="5"></rect>
            <line x1="10" y1="12" x2="14" y2="12"></line>
          </svg>
          历史日报归档清单
        </h3>
        <span style="font-size: 0.85rem; color: var(--text-muted);">
          共显示 {{ filteredReports.length }} 条记录
        </span>
      </div>

      <!-- Loading State -->
      <div v-if="loading && reportsList.length === 0" style="padding: 60px 20px; text-align: center; color: var(--text-muted);">
        <div class="spinner-circle"></div>
        <p style="margin-top: 14px; font-size: 0.92rem;">正在加载历史日报记录...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredReports.length === 0" style="padding: 60px 20px; text-align: center; color: var(--text-muted);">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin: 0 auto 12px; opacity: 0.4;">
          <polyline points="21 8 21 21 3 21 3 8"></polyline>
          <rect x="1" y="3" width="22" height="5"></rect>
          <line x1="10" y1="12" x2="14" y2="12"></line>
        </svg>
        <p style="font-size: 0.95rem; font-weight: 600; color: var(--text-secondary);">暂无符合条件的日报记录</p>
        <p style="font-size: 0.85rem; margin-top: 4px;">您可以尝试调整日期范围或重新刷新</p>
      </div>

      <!-- Data Table -->
      <div v-else class="table-responsive">
        <table class="report-table" id="report-archive-table">
          <thead>
            <tr>
              <th style="width: 130px;">工作日期</th>
              <th style="width: 170px;">推送时间</th>
              <th style="width: 100px;">推送状态</th>
              <th>内容摘要</th>
              <th style="width: 180px;">飞书消息 ID</th>
              <th style="width: 180px; text-align: right;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="rep in filteredReports"
              :key="rep.name"
              class="report-row"
              :class="{ 'row-active': selectedReport?.name === rep.name }"
              @click="selectReport(rep)"
            >
              <td>
                <span class="report-date-badge">{{ rep.report_date }}</span>
              </td>
              <td>
                <span style="font-size: 0.88rem; color: var(--text-secondary);">
                  {{ rep.push_time || '-' }}
                </span>
              </td>
              <td>
                <span :class="getStatusBadgeClass(rep.status)">
                  {{ getStatusText(rep.status) }}
                </span>
              </td>
              <td>
                <div class="report-summary-text" :title="rep.summary">
                  {{ rep.summary || '无摘要内容' }}
                </div>
              </td>
              <td>
                <span class="msg-id-cell" :title="rep.message_id">
                  {{ rep.message_id || '-' }}
                </span>
              </td>
              <td style="text-align: right;">
                <div style="display: inline-flex; align-items: center; gap: 8px;" @click.stop>
                  <button
                    type="button"
                    class="btn-table-action"
                    @click="openDetailModal(rep)"
                    title="查看完整飞书卡片详情"
                  >
                    查看卡片
                  </button>
                  <button
                    type="button"
                    class="btn-table-action-primary"
                    @click="resendReport(rep)"
                    :disabled="resendingMap[rep.name]"
                    title="重新向飞书推送此日报"
                  >
                    <span v-if="resendingMap[rep.name]" class="spinner-sm"></span>
                    <span v-else>重新推送</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Feishu Card Modal / Drawer -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
      <div class="modal-card-container">
        <!-- Modal Header Bar -->
        <div class="modal-top-bar">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div class="modal-badge">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="8" y1="21" x2="16" y2="21"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
              </svg>
            </div>
            <div>
              <h3 style="font-size: 1.1rem; font-weight: 700; color: #fff;">
                飞书日报详情 · {{ activeDetail?.report_date }}
              </h3>
              <p style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.8); margin-top: 2px;">
                记录编号: {{ activeDetail?.name }} | 状态: {{ getStatusText(activeDetail?.status) }}
              </p>
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 12px;">
            <!-- Tab switch: Card Preview vs Raw JSON -->
            <div class="tab-pill-group">
              <button
                type="button"
                :class="['tab-pill-btn', { active: activeDetailTab === 'preview' }]"
                @click="activeDetailTab = 'preview'"
              >
                卡片视觉预览
              </button>
              <button
                type="button"
                :class="['tab-pill-btn', { active: activeDetailTab === 'json' }]"
                @click="activeDetailTab = 'json'"
              >
                原始 JSON
              </button>
            </div>

            <!-- Resend Button in modal -->
            <button
              type="button"
              class="btn-resend-header"
              @click="resendActiveReport"
              :disabled="resendingMap[activeDetail?.name]"
            >
              <span v-if="resendingMap[activeDetail?.name]" class="spinner-sm"></span>
              <span v-else>重新推送飞书</span>
            </button>

            <!-- Close Button -->
            <button type="button" class="btn-close-modal" @click="closeDetailModal">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        <!-- Modal Body Content -->
        <div class="modal-scroll-body">
          <!-- Loading Detail -->
          <div v-if="loadingDetail" style="padding: 60px 20px; text-align: center; color: var(--text-muted);">
            <div class="spinner-circle"></div>
            <p style="margin-top: 14px; font-size: 0.92rem;">正在加载卡片内容详情...</p>
          </div>

          <!-- TAB 1: Authentic Feishu Interactive Card Preview -->
          <div v-else-if="activeDetailTab === 'preview'" class="card-preview-wrapper">
            <!-- Simulated Feishu Client Frame -->
            <div class="feishu-chat-bubble">
              <!-- Lark Card Header -->
              <div
                class="feishu-card-header"
                :class="cardHeaderClass"
              >
                <div class="header-icon">📊</div>
                <div class="header-title">{{ cardTitle }}</div>
              </div>

              <!-- Lark Card Elements Content -->
              <div class="feishu-card-body">
                <!-- Summary bar -->
                <div class="feishu-card-block overview-block">
                  <div style="font-size: 0.92rem; line-height: 1.6; color: var(--text-primary); white-space: pre-line;">
                    {{ cardOverviewText }}
                  </div>
                </div>

                <div class="feishu-card-divider"></div>

                <!-- Projects Dynamic Block -->
                <div class="feishu-card-block">
                  <h4 style="font-size: 0.96rem; font-weight: 700; color: #1f2329; margin-bottom: 8px;">
                    📦 项目研发动态
                  </h4>
                  <div v-if="parsedProjectsText" style="font-size: 0.88rem; line-height: 1.6; color: #333; white-space: pre-line;">
                    {{ parsedProjectsText }}
                  </div>
                  <div v-else style="font-size: 0.88rem; color: var(--text-muted);">
                    当日暂无项目代码提交记录
                  </div>
                </div>

                <div class="feishu-card-divider"></div>

                <!-- Absence Alert Block -->
                <div
                  class="feishu-card-block"
                  :style="hasAbsences ? 'background: #fff5f5; border: 1px solid #fed7d7; border-radius: 6px; padding: 10px 12px;' : ''"
                >
                  <h4
                    style="font-size: 0.96rem; font-weight: 700; margin-bottom: 6px;"
                    :style="{ color: hasAbsences ? '#c53030' : '#2f855a' }"
                  >
                    {{ hasAbsences ? '⚠️ 缺勤提醒 (连续 2 工作日无提交)' : '✅ 全员正常出勤' }}
                  </h4>
                  <div style="font-size: 0.88rem; line-height: 1.6; color: #333; white-space: pre-line;">
                    {{ parsedAbsenceText }}
                  </div>
                </div>

                <!-- Unclaimed Commits Hint (if any) -->
                <div v-if="parsedUnclaimedText" class="feishu-card-block" style="background: #fffaf0; border: 1px solid #feebc8; border-radius: 6px; padding: 10px 12px; margin-top: 12px;">
                  <div style="font-size: 0.88rem; line-height: 1.5; color: #7b341e; white-space: pre-line;">
                    {{ parsedUnclaimedText }}
                  </div>
                </div>

                <div class="feishu-card-divider"></div>

                <!-- Bottom Button: Jump to Daily Activity Page -->
                <div class="feishu-card-action">
                  <button
                    type="button"
                    class="feishu-action-btn"
                    @click="navigateToDailyActivity(activeDetail?.report_date)"
                  >
                    👉 打开研发工作台看板查看详情
                  </button>
                </div>
              </div>
            </div>

            <!-- Side Card Information Column -->
            <div class="card-meta-sidebar">
              <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 12px;">
                推送元数据
              </h4>
              <div class="meta-item">
                <span class="meta-label">工作日期</span>
                <span class="meta-val font-mono">{{ activeDetail?.report_date }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">推送状态</span>
                <span :class="getStatusBadgeClass(activeDetail?.status)">{{ getStatusText(activeDetail?.status) }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">推送时间</span>
                <span class="meta-val">{{ activeDetail?.push_time || '-' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">飞书消息 ID</span>
                <span class="meta-val font-mono" style="word-break: break-all; font-size: 0.78rem;">{{ activeDetail?.message_id || '未记录' }}</span>
              </div>
              <div class="meta-item" style="flex-direction: column; align-items: flex-start; gap: 6px;">
                <span class="meta-label">内容文本摘要</span>
                <div style="font-size: 0.85rem; color: var(--text-secondary); background: #f8fafc; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--border-subtle); line-height: 1.5;">
                  {{ activeDetail?.summary || '无' }}
                </div>
              </div>

              <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-subtle);">
                <button
                  type="button"
                  class="btn-full-primary"
                  @click="navigateToDailyActivity(activeDetail?.report_date)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                  </svg>
                  跳转至该日成员日报
                </button>
              </div>
            </div>
          </div>

          <!-- TAB 2: Raw JSON View -->
          <div v-else class="json-code-wrapper">
            <pre class="json-pre"><code>{{ formattedRawJson }}</code></pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { request, api } from '@/utils/api'

const router = useRouter()

// Filters state
const fromDate = ref('')
const toDate = ref('')
const statusFilter = ref('all')
const currentQuickRange = ref('4w')

// Reports data
const reportsList = ref([])
const loading = ref(false)
const selectedReport = ref(null)

// Detail modal state
const showDetailModal = ref(false)
const loadingDetail = ref(false)
const activeDetail = ref(null)
const activeDetailTab = ref('preview')

// Resending map by docname: boolean
const resendingMap = ref({})

// Notification toast
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (msg, type = 'success') => {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => {
    if (toastMessage.value === msg) {
      toastMessage.value = ''
    }
  }, 4500)
}

// Quick range helpers
const setQuickRange = (rangeKey) => {
  currentQuickRange.value = rangeKey
  const now = new Date()
  const formatDate = (d) => {
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  toDate.value = formatDate(now)

  if (rangeKey === '1w') {
    const past = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    fromDate.value = formatDate(past)
  } else if (rangeKey === '2w') {
    const past = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000)
    fromDate.value = formatDate(past)
  } else if (rangeKey === '4w') {
    const past = new Date(now.getTime() - 28 * 24 * 60 * 60 * 1000)
    fromDate.value = formatDate(past)
  } else if (rangeKey === 'all') {
    fromDate.value = ''
    toDate.value = ''
  }

  fetchReports()
}

// Fetch list of reports
const fetchReports = async () => {
  loading.value = true
  try {
		let url = '/api/method/dev_workbench.api.v1.reports.get_reports_list'
    const params = new URLSearchParams()
    if (fromDate.value) params.append('from_date', fromDate.value)
    if (toDate.value) params.append('to_date', toDate.value)
    if (params.toString()) {
      url += `?${params.toString()}`
    }

		const res = await request(url)
		const data = await res.json()
		reportsList.value = Array.isArray(data.message) ? data.message : []
  } catch (err) {
    console.error('Failed to fetch reports:', err)
  } finally {
    loading.value = false
  }
}

// Filtered list by status
const filteredReports = computed(() => {
  if (statusFilter.value === 'all') {
    return reportsList.value
  }
  return reportsList.value.filter(r => r.status === statusFilter.value)
})

// Metrics
const sentCount = computed(() => reportsList.value.filter(r => r.status === 'Sent').length)
const failedOrDraftCount = computed(() => reportsList.value.filter(r => r.status === 'Failed' || r.status === 'Draft').length)
const latestReportDate = computed(() => {
  if (reportsList.value.length === 0) return ''
  return reportsList.value[0].report_date || ''
})

// Status badge utils
const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'Sent':
      return 'badge-success'
    case 'Draft':
      return 'badge-warning'
    case 'Failed':
      return 'badge-danger'
    case 'Recalled':
      return 'badge-purple'
    default:
      return 'badge-secondary'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'Sent':
      return '已发送'
    case 'Draft':
      return '草稿'
    case 'Failed':
      return '发送失败'
    case 'Recalled':
      return '已撤回'
    default:
      return status || '未知'
  }
}

// Select a row
const selectReport = (rep) => {
  selectedReport.value = rep
}

// Open modal and fetch full detail
const openDetailModal = async (rep) => {
  selectedReport.value = rep
  activeDetail.value = { ...rep }
  activeDetailTab.value = 'preview'
  showDetailModal.value = true
  loadingDetail.value = true

  try {
    const reportKey = rep.name || rep.report_date
		const url = `/api/method/dev_workbench.api.v1.reports.get_report_detail?report_id=${encodeURIComponent(reportKey)}`
		const res = await request(url)
		const data = await res.json()
		activeDetail.value = data.message || {}
  } catch (err) {
    console.error('Failed to load report detail:', err)
  } finally {
    loadingDetail.value = false
  }
}

const closeDetailModal = () => {
  showDetailModal.value = false
}

// Resend report action
const resendReport = async (rep) => {
  const repName = rep.name || rep.report_date
  resendingMap.value[repName] = true

  try {
		const res = await api.post('/api/method/dev_workbench.api.v1.reports.resend_report', { report_id: repName })

    const resData = await res.json()
    const result = resData.message || resData

    if (result.status === 'success' || result.push_status === 'Sent') {
      showToast(`日报 (${rep.report_date}) 重新推送成功！消息ID: ${result.message_id || '已保存'}`, 'success')
      // Update local item
      rep.status = 'Sent'
      if (result.message_id) rep.message_id = result.message_id
      if (result.push_time) rep.push_time = result.push_time
      if (activeDetail.value && activeDetail.value.name === rep.name) {
        activeDetail.value.status = 'Sent'
        activeDetail.value.message_id = result.message_id
        activeDetail.value.push_time = result.push_time
      }
    } else {
      const errDetail = (result.errors && result.errors.length) ? result.errors.join('; ') : (result.message || '发送失败')
      showToast(`重新推送结果: ${errDetail}`, result.status === 'warning' ? 'warning' : 'error')
    }
  } catch (err) {
    console.error('Failed to resend report:', err)
    showToast(`重新推送请求异常: ${err.message}`, 'error')
  } finally {
    resendingMap.value[repName] = false
  }
}

const resendActiveReport = () => {
  if (activeDetail.value) {
    resendReport(activeDetail.value)
  }
}

// Navigate to daily activity page
const navigateToDailyActivity = (dateStr) => {
  closeDetailModal()
  if (dateStr) {
    router.push({
      path: '/dashboard/daily-activity',
      query: { date: dateStr },
    })
  } else {
    router.push('/dashboard/daily-activity')
  }
}

// Card preview parser helpers
const parsedCardObj = computed(() => {
  if (!activeDetail.value) return null
  if (activeDetail.value.card && typeof activeDetail.value.card === 'object') {
    return activeDetail.value.card
  }
  if (activeDetail.value.content) {
    try {
      return JSON.parse(activeDetail.value.content)
    } catch {
      return null
    }
  }
  return null
})

const cardTitle = computed(() => {
  const card = parsedCardObj.value
  return card?.header?.title?.content || `📊 研发效能日报 (${activeDetail.value?.report_date || ''})`
})

const cardHeaderClass = computed(() => {
  const card = parsedCardObj.value
  const tpl = card?.header?.template
  if (tpl === 'carmine' || tpl === 'red') {
    return 'header-carmine'
  }
  return 'header-blue'
})

const cardOverviewText = computed(() => {
  const card = parsedCardObj.value
  if (!card?.elements) return activeDetail.value?.summary || '无概览信息'
  const firstDiv = card.elements.find(el => el.tag === 'div' && el.text?.content?.includes('工作日期'))
  return firstDiv?.text?.content || activeDetail.value?.summary || ''
})

const parsedProjectsText = computed(() => {
  const card = parsedCardObj.value
  if (!card?.elements) return ''
  const projDivs = card.elements.filter(el =>
    el.tag === 'div' &&
    el.text?.content &&
    !el.text.content.includes('工作日期') &&
    !el.text.content.includes('缺勤提醒') &&
    !el.text.content.includes('全员正常出勤') &&
    !el.text.content.includes('未归属提交提示') &&
    el.text.content !== '### 📦 项目研发动态'
  )
  return projDivs.map(d => d.text.content).join('\n\n')
})

const hasAbsences = computed(() => {
  const card = parsedCardObj.value
  if (!card?.elements) return false
  const absenceDiv = card.elements.find(el => el.tag === 'div' && el.text?.content?.includes('缺勤提醒'))
  return !!absenceDiv
})

const parsedAbsenceText = computed(() => {
  const card = parsedCardObj.value
  if (!card?.elements) return '全员正常出勤'
  const absenceDiv = card.elements.find(el =>
    el.tag === 'div' &&
    el.text?.content &&
    (el.text.content.includes('缺勤提醒') || el.text.content.includes('全员正常出勤'))
  )
  return absenceDiv?.text?.content || '全员正常出勤'
})

const parsedUnclaimedText = computed(() => {
  const card = parsedCardObj.value
  if (!card?.elements) return ''
  const unclaimedDiv = card.elements.find(el => el.tag === 'div' && el.text?.content?.includes('未归属提交提示'))
  return unclaimedDiv?.text?.content || ''
})

const formattedRawJson = computed(() => {
  if (!activeDetail.value) return ''
  if (parsedCardObj.value) {
    return JSON.stringify(parsedCardObj.value, null, 2)
  }
  return activeDetail.value.content || '{}'
})

onMounted(() => {
  setQuickRange('4w')
})
</script>

<style scoped>
.report-archive-page {
  animation: fadeIn 0.25s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Metric Cards */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.metric-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-value {
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-top: 2px;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.metric-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon.indigo { background: #e0e7ff; color: #4338ca; }
.metric-icon.emerald { background: #d1fae5; color: #059669; }
.metric-icon.rose { background: #ffe4e6; color: #e11d48; }
.metric-icon.amber { background: #fef3c7; color: #d97706; }
.metric-icon.purple { background: #ede9fe; color: #7c3aed; }

/* Filter Controls */
.form-input-sm {
  height: 34px;
  padding: 4px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  font-size: 0.85rem;
  color: var(--text-primary);
  background: #fff;
  outline: none;
  transition: border-color 0.15s;
}

.form-input-sm:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-glow);
}

.btn-chip {
  height: 32px;
  padding: 0 12px;
  border-radius: 16px;
  border: 1px solid var(--border-subtle);
  background: #f8fafc;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-chip:hover {
  background: #e2e8f0;
  color: var(--text-primary);
}

.btn-chip.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.btn-secondary-sm {
  height: 34px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
  background: #fff;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-secondary-sm:hover:not(:disabled) {
  background: #f1f5f9;
  color: var(--text-primary);
}

.spin-anim {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Alert Banner */
.alert-banner {
  padding: 12px 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.88rem;
  font-weight: 500;
}

.alert-success {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
}

.alert-danger {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

/* Table */
.table-responsive {
  overflow-x: auto;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}

.report-table th {
  background: #f8fafc;
  padding: 12px 16px;
  text-align: left;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
  letter-spacing: 0.02em;
}

.report-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.report-row {
  cursor: pointer;
  transition: background-color 0.15s;
}

.report-row:hover {
  background-color: #f8fafc;
}

.report-row.row-active {
  background-color: #f1f5f9;
}

.report-date-badge {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--primary);
  background: var(--primary-light);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.82rem;
}

.report-summary-text {
  max-width: 420px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
  font-size: 0.88rem;
}

.msg-id-cell {
  display: block;
  max-width: 170px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--text-muted);
}

/* Badges */
.badge-success {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  background: #d1fae5;
  color: #065f46;
}

.badge-warning {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  background: #fef3c7;
  color: #92400e;
}

.badge-danger {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  background: #fee2e2;
  color: #991b1b;
}

.badge-purple {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  background: #ede9fe;
  color: #6d28d9;
}

.badge-secondary {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
}

/* Table Action Buttons */
.btn-table-action {
  height: 28px;
  padding: 0 10px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  background: #fff;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-table-action:hover {
  background: #f1f5f9;
  color: var(--text-primary);
}

.btn-table-action-primary {
  height: 28px;
  padding: 0 10px;
  border-radius: 4px;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  font-size: 0.8rem;
  font-weight: 600;
  color: #4338ca;
  cursor: pointer;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-table-action-primary:hover:not(:disabled) {
  background: #e0e7ff;
  border-color: #a5b4fc;
}

.btn-table-action-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Spinner */
.spinner-circle {
  width: 32px;
  height: 32px;
  margin: 0 auto;
  border: 3px solid #e2e8f0;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-sm {
  width: 12px;
  height: 12px;
  border: 2px solid #a5b4fc;
  border-top-color: #4338ca;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

/* Modal / Drawer */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  animation: modalFadeIn 0.2s ease-out;
}

@keyframes modalFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-card-container {
  width: 100%;
  max-width: 980px;
  max-height: 90vh;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-top-bar {
  background: #1e293b;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-badge {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.tab-pill-group {
  background: rgba(0, 0, 0, 0.25);
  padding: 3px;
  border-radius: 8px;
  display: flex;
  gap: 2px;
}

.tab-pill-btn {
  padding: 6px 12px;
  font-size: 0.82rem;
  font-weight: 500;
  color: #cbd5e1;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.tab-pill-btn.active {
  background: #fff;
  color: #0f172a;
  font-weight: 600;
}

.btn-resend-header {
  height: 32px;
  padding: 0 14px;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-resend-header:hover:not(:disabled) {
  background: #4338ca;
}

.btn-close-modal {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: color 0.15s;
}

.btn-close-modal:hover {
  color: #fff;
}

.modal-scroll-body {
  overflow-y: auto;
  padding: 24px;
  background: #f8fafc;
  flex: 1;
}

/* Card Preview Visual Simulation */
.card-preview-wrapper {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
}

@media (max-width: 820px) {
  .card-preview-wrapper {
    grid-template-columns: 1fr;
  }
}

.feishu-chat-bubble {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #dee0e3;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.feishu-card-header {
  padding: 14px 18px;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 10px;
}

.feishu-card-header.header-blue {
  background: linear-gradient(135deg, #3370ff 0%, #2b5fd9 100%);
}

.feishu-card-header.header-carmine {
  background: linear-gradient(135deg, #d83931 0%, #b82820 100%);
}

.header-icon {
  font-size: 1.25rem;
}

.header-title {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.feishu-card-body {
  padding: 18px;
}

.feishu-card-block {
  margin-bottom: 12px;
}

.feishu-card-divider {
  height: 1px;
  background: #ebeef5;
  margin: 14px 0;
}

.feishu-card-action {
  margin-top: 14px;
}

.feishu-action-btn {
  width: 100%;
  padding: 10px;
  background: #3370ff;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  box-shadow: 0 1px 3px rgba(51, 112, 255, 0.3);
}

.feishu-action-btn:hover {
  background: #2860e1;
}

/* Sidebar Info */
.card-meta-sidebar {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid var(--border-subtle);
  padding: 18px;
  box-shadow: var(--shadow-sm);
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 0.85rem;
}

.meta-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.meta-val {
  color: var(--text-primary);
  font-weight: 600;
}

.font-mono {
  font-family: var(--font-mono);
}

.btn-full-primary {
  width: 100%;
  padding: 10px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.15s;
}

.btn-full-primary:hover {
  background: var(--primary-hover);
}

/* Raw JSON Code */
.json-code-wrapper {
  background: #1e1e2e;
  border-radius: 8px;
  padding: 16px;
  overflow: auto;
  max-height: 520px;
}

.json-pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  line-height: 1.5;
  color: #cdd6f4;
}
</style>
