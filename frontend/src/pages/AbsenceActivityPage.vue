<template>
  <div class="absence-activity-page" id="absence-activity-page">
    <!-- Top Metric Overview Grid -->
    <div class="metric-grid">
      <div class="metric-card" id="metric-card-pending" style="border-color: rgba(239, 68, 68, 0.3); background: #fef2f2;">
        <div>
          <div class="metric-label" style="color: #991b1b;">待跟进缺勤成员</div>
          <div class="metric-value" style="color: #dc2626;">{{ pendingCount }} <span style="font-size: 0.9rem; font-weight: 500; color: #b91c1c;">人</span></div>
        </div>
        <div class="metric-icon rose">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-exempted">
        <div>
          <div class="metric-label">已请假豁免成员</div>
          <div class="metric-value" style="color: #2563eb;">{{ exemptedCount }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">人</span></div>
        </div>
        <div class="metric-icon indigo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-total">
        <div>
          <div class="metric-label">缺勤预警总记录</div>
          <div class="metric-value">{{ absenceList.length }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">人</span></div>
        </div>
        <div class="metric-icon amber">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-date">
        <div>
          <div class="metric-label">核查工作日规则</div>
          <div class="metric-value" style="font-size: 1.15rem; margin-top: 4px;">连续 2 工作日</div>
        </div>
        <div class="metric-icon emerald">
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
          <!-- Date Filter -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">核查日期：</label>
            <input
              id="filter-absence-date"
              type="date"
              v-model="selectedDate"
              @change="fetchAbsences"
              class="form-input-sm"
            />
            <button type="button" class="btn-chip" @click="setDateOffset(-1)">昨天</button>
            <button type="button" class="btn-chip" @click="setDateOffset(0)">今天</button>
          </div>

          <!-- Project Filter -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">项目筛选：</label>
            <select
              id="filter-absence-project"
              v-model="selectedProject"
              @change="fetchAbsences"
              class="form-input-sm"
              style="min-width: 130px;"
            >
              <option value="">全部项目</option>
              <option v-for="p in availableProjects" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>

          <!-- Exemption Status Filter -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">状态：</label>
            <select
              id="filter-absence-status"
              v-model="statusFilter"
              class="form-input-sm"
            >
              <option value="all">全部记录</option>
              <option value="pending">仅待跟进 (未豁免)</option>
              <option value="exempted">仅已请假豁免</option>
            </select>
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 12px;">
          <router-link to="/exemptions" class="btn-secondary" style="font-size: 0.86rem; padding: 7px 14px;">
            📝 管理请假豁免规则
          </router-link>
          <button
            type="button"
            class="btn-primary"
            style="font-size: 0.86rem; padding: 7px 14px;"
            :disabled="checking"
            @click="triggerCheck"
          >
            {{ checking ? '正在核查...' : '🔄 重新核查缺勤' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" style="text-align: center; padding: 60px 0; background: #fff; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
      <div class="spinner" style="display: inline-block; width: 36px; height: 36px; border: 3px solid #e2e8f0; border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
      <div style="margin-top: 14px; font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">正在加载缺勤记录...</div>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredList.length === 0" class="empty-frame" id="absence-empty-frame">
      <div class="empty-icon" style="color: #059669; background: #ecfdf5;">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
      </div>
      <h3 class="empty-title">全员出勤正常，无缺勤报警</h3>
      <p class="empty-desc">
        在核查日期（{{ selectedDate }}）基准下，所有在职开发者在过去 2 个法定工作日内均有正常代码提交记录，团队研发节奏健康推进。
      </p>
      <div style="display: flex; justify-content: center; gap: 12px;">
        <router-link to="/dashboard/daily-activity" class="btn-secondary">查看今日成员日报</router-link>
        <router-link to="/exemptions" class="btn-secondary">查看豁免记录表</router-link>
      </div>
    </div>

    <!-- Table Card -->
    <div v-else class="table-card" style="background: #fff; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;">
        <div style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
          <span>⚠️ 连续无提交成员明细列表</span>
          <span style="font-size: 0.8rem; font-weight: 500; color: #dc2626; background: #fef2f2; padding: 2px 8px; border-radius: 12px; border: 1px solid #fee2e2;">
            共 {{ filteredList.length }} 位成员
          </span>
        </div>
        <div style="font-size: 0.82rem; color: var(--text-muted);">
          根据国家法定节假日及调休补班日历自动计算
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table class="activity-table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 1px solid var(--border-medium); color: var(--text-secondary); font-weight: 600;">
              <th style="padding: 12px 18px; width: 170px;">成员姓名</th>
              <th style="padding: 12px 18px; width: 130px; text-align: center;">无提交天数</th>
              <th style="padding: 12px 18px; width: 140px;">豁免状态</th>
              <th style="padding: 12px 18px;">豁免原因 / 备注说明</th>
              <th style="padding: 12px 18px; width: 160px;">最近一次提交日期</th>
              <th style="padding: 12px 18px; width: 150px; text-align: right;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in filteredList"
              :key="item.name || item.member_id"
              class="table-row"
              style="border-bottom: 1px solid var(--border-subtle); transition: background 0.15s;"
            >
              <!-- Member Info -->
              <td style="padding: 14px 18px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                  <div
                    class="avatar-circle"
                    :style="item.is_exempted ? 'background: #eff6ff; color: #2563eb;' : 'background: #fee2e2; color: #dc2626;'"
                  >
                    {{ (item.member_name || item.member_id).slice(0, 2) }}
                  </div>
                  <div>
                    <div style="font-weight: 600; color: var(--text-primary);">{{ item.member_name || item.member_id }}</div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">{{ item.email || item.member_id }}</div>
                  </div>
                </div>
              </td>

              <!-- Consecutive Days -->
              <td style="padding: 14px 18px; text-align: center;">
                <span class="badge-days">连续 {{ item.consecutive_workdays || 2 }} 工作日</span>
              </td>

              <!-- Status Badge -->
              <td style="padding: 14px 18px;">
                <span v-if="item.is_exempted" class="badge-exempted">
                  🔵 已请假豁免
                </span>
                <span v-else class="badge-pending">
                  🔴 待跟进
                </span>
              </td>

              <!-- Exemption Reason -->
              <td style="padding: 14px 18px; color: var(--text-secondary);">
                <div v-if="item.is_exempted" style="font-size: 0.85rem; color: #1e40af;">
                  {{ item.exemption_reason || '已登记请假豁免' }}
                </div>
                <div v-else style="font-size: 0.82rem; color: var(--text-muted);">
                  未匹配到有效请假豁免记录，需跟进是否有线下请假或未认领邮箱
                </div>
              </td>

              <!-- Last Commit Date -->
              <td style="padding: 14px 18px; color: var(--text-secondary); font-size: 0.85rem;">
                {{ item.last_commit_date || '无近期提交' }}
              </td>

              <!-- Action Buttons -->
              <td style="padding: 14px 18px; text-align: right;">
                <button
                  v-if="!item.is_exempted"
                  type="button"
                  class="btn-primary"
                  style="padding: 5px 12px; font-size: 0.82rem;"
                  @click="openExemptionModal(item)"
                >
                  标记请假豁免
                </button>
                <span v-else style="font-size: 0.82rem; color: #059669; font-weight: 600;">
                  ✓ 已豁免
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Quick Exemption Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">
            📝 快速标记请假豁免
          </div>
          <button type="button" class="btn-close" @click="showModal = false">✕</button>
        </div>

        <div style="padding: 20px;">
          <div class="form-group" style="margin-bottom: 16px;">
            <label style="display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px;">豁免成员：</label>
            <input type="text" :value="modalData.member_name" disabled class="form-input" style="background: #f1f5f9;" />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
            <div>
              <label style="display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px;">起始日期：</label>
              <input type="date" v-model="modalData.start_date" class="form-input" />
            </div>
            <div>
              <label style="display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px;">截止日期：</label>
              <input type="date" v-model="modalData.end_date" class="form-input" />
            </div>
          </div>

          <div class="form-group" style="margin-bottom: 20px;">
            <label style="display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px;">豁免原因 / 事由：</label>
            <input
              type="text"
              v-model="modalData.reason"
              placeholder="例如：年假休假、外出公干、项目调研等"
              class="form-input"
            />
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button type="button" class="btn-secondary" @click="showModal = false">取消</button>
            <button type="button" class="btn-primary" :disabled="submittingModal" @click="submitExemption">
              {{ submittingModal ? '提交中...' : '确认标记并生效' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { request, api } from '@/utils/api'

const getTodayStr = () => {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const selectedDate = ref(getTodayStr())
const selectedProject = ref('')
const statusFilter = ref('all')
const loading = ref(false)
const checking = ref(false)
const absenceList = ref([])
const availableProjects = ref([])

const showModal = ref(false)
const submittingModal = ref(false)
const modalData = ref({
  member_id: '',
  member_name: '',
  start_date: '',
  end_date: '',
  reason: '',
})

const pendingCount = computed(() => {
  return absenceList.value.filter(item => !item.is_exempted).length
})

const exemptedCount = computed(() => {
  return absenceList.value.filter(item => item.is_exempted).length
})

const filteredList = computed(() => {
  let list = [...absenceList.value]

  if (statusFilter.value === 'pending') {
    list = list.filter(item => !item.is_exempted)
  } else if (statusFilter.value === 'exempted') {
    list = list.filter(item => item.is_exempted)
  }

  return list
})

const setDateOffset = (offsetDays) => {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  selectedDate.value = `${year}-${month}-${day}`
  fetchAbsences()
}

const fetchAbsences = async () => {
  loading.value = true
  try {
		let url = `/api/method/dev_workbench.api.v1.absence.get_absence_list?date=${encodeURIComponent(selectedDate.value)}&include_exempted=1`
    if (selectedProject.value) {
      url += `&project=${encodeURIComponent(selectedProject.value)}`
    }

    const res = await request(url)
    const json = await res.json()
    const data = json.message || json
    absenceList.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('获取缺勤记录异常:', err)
  } finally {
    loading.value = false
  }
}

const triggerCheck = async () => {
  if (checking.value) return
  checking.value = true
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.absence.trigger_absence_check', { date: selectedDate.value })
    await fetchAbsences()
  } catch (e) {
    console.error('触发缺勤检测异常:', e)
  } finally {
    checking.value = false
  }
}

const openExemptionModal = (item) => {
  modalData.value = {
    member_id: item.member_id || item.member,
    member_name: item.member_name || item.member_id,
    start_date: selectedDate.value,
    end_date: selectedDate.value,
    reason: '事假/调休',
  }
  showModal.value = true
}

const submitExemption = async () => {
  if (!modalData.value.start_date || !modalData.value.end_date) {
    alert('请选择起止日期')
    return
  }
  submittingModal.value = true
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.absence.grant_exemption', modalData.value)
    const json = await res.json()
    if (res.ok) {
      showModal.value = false
      await fetchAbsences()
    } else {
      alert(`标记豁免失败: ${json.message || '未知错误'}`)
    }
  } catch (err) {
    alert(`网络请求异常: ${err.message}`)
  } finally {
    submittingModal.value = false
  }
}

onMounted(() => {
  fetchAbsences()
})
</script>

<style scoped>
.form-input-sm {
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-medium);
  font-family: inherit;
  font-size: 0.88rem;
  color: var(--text-primary);
  outline: none;
  background: #fff;
}

.btn-chip {
  padding: 4px 10px;
  background: #f1f5f9;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-chip:hover {
  background: #e2e8f0;
}

.avatar-circle {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.82rem;
  font-weight: 700;
  flex-shrink: 0;
}

.badge-days {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  background: #fef2f2;
  color: #b91c1c;
  font-weight: 600;
  font-size: 0.8rem;
}

.badge-exempted {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid #bfdbfe;
}

.badge-pending {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid #fecaca;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-width: 460px;
  overflow: hidden;
  animation: fadeIn 0.15s ease-out;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.2rem;
  color: var(--text-muted);
  cursor: pointer;
}

.btn-close:hover {
  color: var(--text-primary);
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-medium);
  font-family: inherit;
  font-size: 0.88rem;
  color: var(--text-primary);
  outline: none;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--primary);
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}
</style>
