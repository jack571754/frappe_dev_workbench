<template>
  <div class="daily-activity-page" id="daily-activity-page">
    <!-- Token Expiry Warning Alert -->
    <div
      v-if="tokenAlert && tokenAlert.need_attention"
      style="margin-bottom: 20px; padding: 12px 18px; border-radius: var(--radius-md); background: #fffbeb; border: 1px solid #fde68a; display: flex; align-items: center; justify-content: space-between; gap: 16px;"
    >
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 1.1rem;">⚠️</span>
        <div style="font-size: 0.86rem; color: #92400e;">
          <strong>Codeup 访问令牌预警：</strong>
          当前令牌将于 {{ tokenAlert.global_expires_at }} 到期（有效剩余 {{ tokenAlert.days_left }} 天），为避免代码拉取和日报统计中断，请及时更新。
        </div>
      </div>
      <router-link
        to="/repositories"
        class="btn-secondary"
        style="padding: 4px 12px; font-size: 0.8rem; background: #ffffff; border-color: #f59e0b; color: #b45309;"
      >
        前往更新凭证
      </router-link>
    </div>

    <!-- Top Metric Overview Grid -->
    <div class="metric-grid">
      <div class="metric-card" id="metric-card-members">
        <div>
          <div class="metric-label">活跃提交成员</div>
          <div class="metric-value">{{ metrics.active_members_count }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">人</span></div>
        </div>
        <div class="metric-icon indigo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-lines">
        <div>
          <div class="metric-label">变更代码总行数</div>
          <div class="metric-value">{{ formatNumber(metrics.total_lines) }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">行</span></div>
        </div>
        <div class="metric-icon emerald">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="16 18 22 12 16 6"></polyline>
            <polyline points="8 6 2 12 8 18"></polyline>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-commits">
        <div>
          <div class="metric-label">代码提交次数</div>
          <div class="metric-value">{{ metrics.total_commits }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">次</span></div>
        </div>
        <div class="metric-icon amber">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="18" cy="18" r="3"></circle>
            <circle cx="6" cy="6" r="3"></circle>
            <path d="M13 6h3a2 2 0 0 1 2 2v7"></path>
            <line x1="6" y1="9" x2="6" y2="21"></line>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-card-unclaimed" :style="metrics.unclaimed_commits > 0 ? 'border-color: rgba(239, 68, 68, 0.4); background: #fff5f5;' : ''">
        <div>
          <div class="metric-label">未归属提交次数</div>
          <div class="metric-value" :style="metrics.unclaimed_commits > 0 ? 'color: var(--danger);' : ''">
            {{ metrics.unclaimed_commits }} <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">次</span>
          </div>
        </div>
        <div class="metric-icon rose">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
      </div>
    </div>

    <!-- Filters Bar: 从左到右依次排列 -->
    <div class="filter-panel" id="filter-panel-card">
      <div class="filter-row-container">
        <!-- 1. 查询模式 -->
        <div class="filter-item">
          <span class="filter-label">查询模式：</span>
          <div class="mode-tabs">
            <button
              type="button"
              :class="['mode-tab', queryMode === 'single' ? 'active' : '']"
              @click="setQueryMode('single')"
            >
              单日日报
            </button>
            <button
              type="button"
              :class="['mode-tab', queryMode === 'range' ? 'active' : '']"
              @click="setQueryMode('range')"
            >
              周期范围
            </button>
          </div>
        </div>

        <!-- 2. 日期选择 -->
        <div v-if="queryMode === 'single'" class="filter-item">
          <span class="filter-label">活动日期：</span>
          <input
            id="filter-date-input"
            type="date"
            v-model="selectedDate"
            @change="fetchData"
            class="form-input-sm"
          />
          <div class="btn-group-chips">
            <button type="button" class="btn-chip" @click="setDateOffset(-1)">昨天</button>
            <button type="button" class="btn-chip" @click="setDateOffset(-2)">前天</button>
          </div>
        </div>

        <div v-else class="filter-item">
          <span class="filter-label">日期区间：</span>
          <input
            type="date"
            v-model="startDate"
            class="form-input-sm"
          />
          <span class="date-sep">至</span>
          <input
            type="date"
            v-model="endDate"
            class="form-input-sm"
          />
          <div class="btn-group-chips">
            <button type="button" class="btn-chip" @click="setPastDays(7)">近7天</button>
            <button type="button" class="btn-chip" @click="setPastDays(14)">近14天</button>
            <button type="button" class="btn-chip" @click="setPastDays(30)">近30天</button>
          </div>
          <button type="button" class="btn-secondary btn-sm" style="padding: 4px 10px; font-size: 0.82rem;" @click="fetchData">查询</button>
        </div>

        <!-- 3. 成员筛选 -->
        <div class="filter-item" id="filter-member-item">
          <span class="filter-label">成员：</span>
          <div class="filter-select-box">
            <MultiSelect
              id="filter-member-select"
              v-model="selectedMembers"
              :options="memberOptions"
              placeholder="全部成员"
              @update:modelValue="fetchData"
            />
          </div>
        </div>

        <!-- 4. 所属项目 -->
        <div class="filter-item" id="filter-project-item">
          <span class="filter-label">项目：</span>
          <div class="filter-select-box">
            <MultiSelect
              id="filter-project-select"
              v-model="selectedProjects"
              :options="projectOptions"
              placeholder="全部项目"
              @update:modelValue="fetchData"
            />
          </div>
        </div>

        <!-- 5. 代码仓库 -->
        <div class="filter-item" id="filter-repo-item">
          <span class="filter-label">仓库：</span>
          <div class="filter-select-box">
            <MultiSelect
              id="filter-repository-select"
              v-model="selectedRepos"
              :options="repoOptions"
              placeholder="全部代码仓库"
              @update:modelValue="fetchData"
            />
          </div>
        </div>

        <!-- 6. 代码分支 -->
        <div class="filter-item" id="filter-branch-item">
          <span class="filter-label">分支：</span>
          <div class="filter-select-box">
            <MultiSelect
              id="filter-branch-select"
              v-model="selectedBranches"
              :options="branchOptions"
              placeholder="全部分支"
              @update:modelValue="handleBranchChange"
            />
          </div>
        </div>

        <!-- 7. 重置筛选 -->
        <button
          v-if="hasActiveFilters"
          id="btn-reset-filters"
          type="button"
          class="btn-reset"
          @click="resetAllFilters"
          title="清空并重置所有多选筛选条件"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
          重置
        </button>


      </div>
    </div>

    <!-- Alert Banner: Unclaimed Commits Hint -->
    <div
      v-if="unclaimedData && unclaimedData.commit_count > 0 && !selectedMembers.includes('unclaimed')"
      class="unclaimed-banner"
      style="margin-bottom: 20px; background: #fffbeb; border: 1px solid #fde68a; border-radius: var(--radius-md); padding: 12px 18px; display: flex; align-items: center; justify-content: space-between;"
    >
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 1.2rem;">⚠️</span>
        <div style="font-size: 0.88rem; color: #92400e;">
          检测到当前日期区间有 <strong>{{ unclaimedData.commit_count }}</strong> 条未关联到项目成员的 Git 提交（代码量 {{ unclaimedData.total_lines }} 行），请管理者及时认领。
        </div>
      </div>
      <div style="display: flex; gap: 10px;">
        <button
          type="button"
          class="btn-secondary"
          style="padding: 4px 12px; font-size: 0.82rem; border-color: #f59e0b; color: #b45309;"
          @click="showUnclaimedOnlyHandler"
        >
          查看未归属列表
        </button>
        <router-link
          to="/members"
          class="btn-primary"
          style="padding: 4px 12px; font-size: 0.82rem;"
        >
          前往认领身份
        </router-link>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" style="text-align: center; padding: 60px 0; background: #fff; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
      <div class="spinner" style="display: inline-block; width: 36px; height: 36px; border: 3px solid #e2e8f0; border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
      <div style="margin-top: 14px; font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">正在加载成员提交活动数据...</div>
    </div>

    <!-- Empty State -->
    <div v-else-if="displayedRows.length === 0" class="empty-frame" id="daily-activity-empty-frame">
      <div class="empty-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
      </div>
      <h3 class="empty-title">所选周期暂无成员提交数据</h3>
      <p class="empty-desc">
        当前所选日期（{{ queryMode === 'single' ? selectedDate : `${startDate} ~ ${endDate}` }}）暂未匹配到代码提交记录。可通过右上角【立即刷新】同步最新提交，或前往【仓库配置】确认已关联代码库与令牌有效。
      </p>
      <div style="display: flex; justify-content: center; gap: 12px;">
        <router-link to="/repositories" class="btn-secondary" id="btn-goto-repositories">
          配置代码仓库
        </router-link>
        <router-link to="/members" class="btn-secondary" id="btn-goto-members">
          管理成员身份
        </router-link>
      </div>
    </div>

    <!-- Main Activity Table Card -->
    <div v-else class="table-card" style="background: #fff; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;">
        <div style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
          <span>成员工作量明细</span>
          <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-muted); background: #f1f5f9; padding: 2px 8px; border-radius: 12px;">
            共 {{ displayedRows.length }} 位成员
          </span>
        </div>
        <div v-if="selectedMembers.length > 0" style="font-size: 0.82rem; color: var(--primary); cursor: pointer;" @click="clearMemberFilter">
          ✕ 清除成员筛选，查看全部
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table class="activity-table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 1px solid var(--border-medium); color: var(--text-secondary); font-weight: 600;">
              <th style="padding: 12px 18px; width: 160px;">开发者姓名</th>
              <th style="padding: 12px 18px; width: 180px;">所属项目与代码仓库</th>
              <th style="padding: 12px 18px; width: 110px; text-align: center;">提交次数</th>
              <th style="padding: 12px 18px; width: 160px;">代码变更行数</th>
              <th style="padding: 12px 18px; width: 110px; text-align: center;">涉及文件</th>
              <th style="padding: 12px 18px;">工作摘要</th>
              <th style="padding: 12px 18px; width: 120px; text-align: right;">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in displayedRows" :key="item.member_id">
              <tr
                :class="['table-row', expandedMemberId === item.member_id ? 'expanded-row' : '']"
                style="border-bottom: 1px solid var(--border-subtle); transition: background 0.15s;"
              >
                <!-- Member Name & Dept -->
                <td style="padding: 14px 18px;">
                  <div style="display: flex; align-items: center; gap: 10px;">
                    <div
                      class="avatar-circle"
                      :style="item.member_id === 'unclaimed' ? 'background: #fee2e2; color: #ef4444;' : 'background: #e0e7ff; color: #4338ca;'"
                    >
                      {{ item.member_name.slice(0, 2) }}
                    </div>
                    <div>
                      <div style="font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
                        <span>{{ item.member_name }}</span>
                        <span v-if="item.is_manager" class="badge-role">主管</span>
                      </div>
                      <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">
                        {{ item.department || item.email || (item.member_id === 'unclaimed' ? '未绑定成员' : item.member_id) }}
                      </div>
                    </div>
                  </div>
                </td>

                <!-- Projects & Repositories Badges -->
                <td style="padding: 14px 18px;">
                  <div style="display: flex; flex-direction: column; gap: 5px;">
                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                      <span v-for="p in item.projects" :key="p" class="badge-project">{{ p }}</span>
                      <span v-if="!item.projects || item.projects.length === 0" style="color: var(--text-muted); font-size: 0.8rem;">未指定项目</span>
                    </div>
                    <div v-if="item.repositories && item.repositories.length" style="display: flex; flex-wrap: wrap; gap: 4px;">
                      <span
                        v-for="r in item.repositories"
                        :key="r"
                        style="font-size: 0.72rem; padding: 1px 6px; border-radius: 4px; background: #eef2ff; color: #4338ca; border: 1px solid #c7d2fe; font-weight: 500;"
                      >
                        📦 {{ r }}
                      </span>
                    </div>
                  </div>
                </td>

                <!-- Commits Count -->
                <td style="padding: 14px 18px; text-align: center;">
                  <span class="badge-count">{{ item.commit_count }}</span>
                </td>

                <!-- Lines Changes -->
                <td style="padding: 14px 18px;">
                  <div style="font-weight: 600; color: var(--text-primary);">
                    {{ formatNumber(item.total_lines) }} <span style="font-weight: normal; font-size: 0.78rem; color: var(--text-muted);">行</span>
                  </div>
                  <div style="font-size: 0.75rem; margin-top: 3px; display: flex; gap: 6px;">
                    <span style="color: #059669;">+{{ formatNumber(item.lines_added) }}</span>
                    <span style="color: #dc2626;">-{{ formatNumber(item.lines_deleted) }}</span>
                    <span v-if="item.lines_unknown" class="badge-warn" title="部分提交未返回行数明细">行数未知</span>
                  </div>
                </td>

                <!-- File Count -->
                <td style="padding: 14px 18px; text-align: center; color: var(--text-secondary); font-weight: 500;">
                  {{ item.file_count }}
                </td>

                <!-- AI Summary -->
                <td style="padding: 14px 18px;">
                  <div class="summary-box">
                    <span style="color: var(--text-primary);">{{ item.summary || '暂无工作摘要' }}</span>
                  </div>
                </td>

                <!-- Actions -->
                <td style="padding: 14px 18px; text-align: right;">
                  <button v-if="item.member_id !== 'unclaimed' && item.commit_count > 0" type="button" class="btn-secondary" style="padding: 5px 10px; font-size: 0.8rem; margin-bottom: 6px;" @click="reviewMember = item">AI 审查</button>
                  <button
                    type="button"
                    class="btn-secondary"
                    style="padding: 5px 10px; font-size: 0.8rem;"
                    @click="toggleExpand(item.member_id)"
                  >
                    {{ expandedMemberId === item.member_id ? '收起明细 ▲' : `提交记录 (${item.commit_count}) ▼` }}
                  </button>
                </td>
              </tr>

              <!-- Expanded Commits Details Row -->
              <tr v-if="expandedMemberId === item.member_id" class="detail-row">
                <td colspan="7" style="padding: 16px 24px; background: #f8fafc; border-bottom: 2px solid var(--border-medium);">
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <div style="font-size: 0.88rem; font-weight: 700; color: var(--text-secondary); display: flex; align-items: center; gap: 8px;">
                      <span>🔍 {{ item.member_name }} 的具体提交列表</span>
                      <span style="font-size: 0.78rem; font-weight: normal; color: var(--text-muted);">(北京时间 UTC+8，已去重及排除 Merge Commit)</span>
                    </div>
                    <div v-if="item.member_id === 'unclaimed'">
                      <router-link to="/members" class="btn-primary" style="padding: 4px 10px; font-size: 0.8rem;">
                        👉 立即为这些提交认领 Git 身份
                      </router-link>
                    </div>
                  </div>

                  <!-- Commits List -->
                  <div v-if="item.commits && item.commits.length > 0" style="display: flex; flex-direction: column; gap: 8px;">
                    <div
                      v-for="(c, cIdx) in item.commits"
                      :key="c.id || cIdx"
                      class="commit-card"
                      style="background: #fff; padding: 10px 14px; border-radius: 6px; border: 1px solid var(--border-subtle); display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;"
                    >
                      <div style="display: flex; align-items: flex-start; gap: 10px;">
                        <span class="commit-sha">{{ (c.shortId || c.id || '').slice(0, 8) }}</span>
                        <div>
                          <div style="font-weight: 600; color: var(--text-primary); font-size: 0.86rem; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                            <span>{{ c.title || c.message || '无提交标题' }}</span>
                            <span v-if="c.repository" style="font-size: 0.72rem; font-weight: 500; padding: 1px 6px; border-radius: 4px; background: #eef2ff; color: #4338ca; border: 1px solid #c7d2fe;">
                              📦 {{ c.repository }}
                            </span>
                          </div>
                          <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 3px; display: flex; gap: 12px; flex-wrap: wrap;">
                            <span>提交时间: {{ formatBeijingDate(c.authoredDate || c.authored_date) }}</span>
                            <span v-if="c.authorEmail">邮箱: {{ c.authorEmail }}</span>
                            <span v-if="c.branch">分支: {{ c.branch }}</span>
                          </div>
                        </div>
                      </div>

                      <!-- Changed Files Count Tag -->
                      <div style="font-size: 0.78rem; color: var(--text-muted); white-space: nowrap;">
                        <span v-if="c.files && c.files.length">{{ c.files.length }} 个修改文件</span>
                        <span v-else-if="c.stats">{{ c.stats.total || 0 }} 行变更</span>
                      </div>
                    </div>
                  </div>

                  <div v-else style="padding: 14px; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: #fff; border-radius: 6px;">
                    暂无原始提交记录详情
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
  <CodeReviewCreateDialog v-if="reviewMember" :member="reviewMember.member_id" :start-date="queryMode === 'single' ? selectedDate : startDate" :end-date="queryMode === 'single' ? selectedDate : endDate" :scope="currentScope" :repositories="extractValues(selectedRepos)" :shas="(reviewMember.commits || []).map(c => c.id)" @close="reviewMember = null" />
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { MultiSelect } from 'frappe-ui'
import { request } from '@/utils/api'
import CodeReviewCreateDialog from '@/components/CodeReviewCreateDialog.vue'

const reviewMember = ref(null)

const route = useRoute()

const getYesterdayStr = () => {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const queryMode = ref('single')
const selectedDate = ref(getYesterdayStr())
const startDate = ref(getYesterdayStr())
const endDate = ref(getYesterdayStr())

// 多选筛选响应式状态 (array of string values)
const selectedMembers = ref([])
const selectedProjects = ref([])
const selectedRepos = ref([])
const selectedBranches = ref([])

const allMembers = ref([])
const availableProjects = ref([])
const availableRepositories = ref([])
const availableBranches = ref([])
const membersList = ref([])
const unclaimedData = ref(null)
const tokenAlert = ref(null)

const extractValues = (arr) => {
  if (!arr) return []
  if (!Array.isArray(arr)) return [arr].filter(Boolean)
  return arr.map(item => (typeof item === 'object' && item !== null ? item.value : item)).filter(Boolean)
}

const memberOptions = computed(() => {
  const source = allMembers.value.length > 0 ? allMembers.value : membersList.value
  const opts = source.map(m => ({
    label: m.member_name ? `${m.member_name} (${m.department || m.member_id})` : m.member_id,
    value: m.member_id,
  }))
  // 仅在当前存在未归属提交数据时才展示未归属选项
  if (unclaimedData.value && unclaimedData.value.commit_count > 0) {
    opts.push({
      label: `⚠️ 未归属提交 (${unclaimedData.value.commit_count})`,
      value: 'unclaimed',
    })
  }
  return opts
})

const projectOptions = computed(() => {
  return availableProjects.value.map(p => ({
    label: p,
    value: p,
  }))
})

const repoOptions = computed(() => {
  return availableRepositories.value.map(r => ({
    label: `📦 ${r}`,
    value: r,
  }))
})

const branchOptions = computed(() => {
  return availableBranches.value.map(b => ({
    label: `🌿 ${b}`,
    value: b,
  }))
})

const hasActiveFilters = computed(() => {
  return (
    selectedMembers.value.length > 0 ||
    selectedProjects.value.length > 0 ||
    selectedRepos.value.length > 0 ||
    selectedBranches.value.length > 0
  )
})

const resetAllFilters = () => {
  selectedMembers.value = []
  selectedProjects.value = []
  selectedRepos.value = []
  selectedBranches.value = []
  localStorage.removeItem('dev_workbench_selected_branch')
  window.dispatchEvent(new CustomEvent('dev_workbench_branch_changed', { detail: { branch: '' } }))
  fetchData()
}

const handleBranchChange = () => {
  const branches = extractValues(selectedBranches.value)
  const branchStr = branches.join(',')
  localStorage.setItem('dev_workbench_selected_branch', branchStr)
  fetchData()
}

const handleBranchChanged = (e) => {
  const b = e.detail?.branch
  if (Array.isArray(b)) {
    selectedBranches.value = b
  } else if (b) {
    selectedBranches.value = b.split(',').map(s => s.trim()).filter(Boolean)
  } else {
    selectedBranches.value = []
  }
  fetchData()
}

const showUnclaimedOnlyHandler = () => {
  selectedMembers.value = ['unclaimed']
  fetchData()
}

const clearMemberFilter = () => {
  selectedMembers.value = []
  fetchData()
}

const handleRefreshed = () => {
  fetchData()
}

const checkTokenStatus = async () => {
  try {
    const res = await request('/api/method/dev_workbench.api.v1.settings.get_token_status')
    const json = await res.json()
    const data = json.message || json
    if (data && data.summary) {
      tokenAlert.value = data.summary
    }
  } catch (e) {}
}
const currentScope = ref(localStorage.getItem('dev_workbench_branch_scope') || 'all')

const loading = ref(false)
const expandedMemberId = ref(null)

const metrics = ref({
  active_members_count: 0,
  total_commits: 0,
  total_lines: 0,
  unclaimed_commits: 0,
  absent_count: 0,
})

const isShowingUnclaimedOnly = computed(() => {
  const activeMembers = extractValues(selectedMembers.value)
  return activeMembers.length === 1 && activeMembers[0] === 'unclaimed'
})

const displayedRows = computed(() => {
  let list = [...membersList.value]
  const activeMembers = extractValues(selectedMembers.value)
  const showUnclaimedOnly = activeMembers.length === 1 && activeMembers[0] === 'unclaimed'

  if (showUnclaimedOnly) {
    return (unclaimedData.value && unclaimedData.value.commit_count > 0) ? [unclaimedData.value] : []
  }

  const showUnclaimed = activeMembers.length === 0 || activeMembers.includes('unclaimed')
  if (showUnclaimed && unclaimedData.value && unclaimedData.value.commit_count > 0) {
    if (!list.some(item => item.member_id === 'unclaimed')) {
      list.push(unclaimedData.value)
    }
  }

  return list
})

const setQueryMode = (mode) => {
  queryMode.value = mode
  if (mode === 'single') {
    fetchData()
  } else {
    setPastDays(7)
  }
}

const setDateOffset = (offsetDays) => {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  selectedDate.value = `${year}-${month}-${day}`
  fetchData()
}

const setPastDays = (days) => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - days + 1)

  const format = (d) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }

  startDate.value = format(start)
  endDate.value = format(end)
  fetchData()
}

const toggleExpand = (memberId) => {
  if (expandedMemberId.value === memberId) {
    expandedMemberId.value = null
  } else {
    expandedMemberId.value = memberId
  }
}

const formatNumber = (num) => {
  if (!num) return '0'
  return Number(num).toLocaleString('en-US')
}

const formatBeijingDate = (dateStr) => {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return dateStr
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    let url = `/api/method/dev_workbench.api.v1.activity.get_daily_overview?scope=${encodeURIComponent(currentScope.value)}`
    if (queryMode.value === 'single') {
      url += `&date=${encodeURIComponent(selectedDate.value)}`
    } else {
      url += `&start_date=${encodeURIComponent(startDate.value)}&end_date=${encodeURIComponent(endDate.value)}`
    }
    const projects = extractValues(selectedProjects.value)
    if (projects.length > 0) {
      url += `&project=${encodeURIComponent(projects.join(','))}`
    }
    const repos = extractValues(selectedRepos.value)
    if (repos.length > 0) {
      url += `&repository=${encodeURIComponent(repos.join(','))}`
    }
    const branches = extractValues(selectedBranches.value)
    if (branches.length > 0) {
      url += `&branch=${encodeURIComponent(branches.join(','))}`
    }
    const members = extractValues(selectedMembers.value)
    if (members.length > 0) {
      url += `&member=${encodeURIComponent(members.join(','))}`
    }

    const res = await request(url)
    const json = await res.json()
    const data = json.message || json

    metrics.value = data.metrics || {
      active_members_count: 0,
      total_commits: 0,
      total_lines: 0,
      unclaimed_commits: 0,
      absent_count: 0,
    }

    allMembers.value = data.all_members || []
    availableProjects.value = data.projects || []
    if (data.repositories) {
      availableRepositories.value = data.repositories
    }
    if (data.available_branches || data.branches) {
      availableBranches.value = data.available_branches || data.branches
    }
    membersList.value = data.members || []
    unclaimedData.value = data.unclaimed || null
  } catch (err) {
    console.error('获取成员活动数据异常:', err)
  } finally {
    loading.value = false
  }
}



const handleScopeChanged = (e) => {
  currentScope.value = e.detail?.scope || 'all'
  fetchData()
}

onMounted(() => {
  if (route.query.date) {
    selectedDate.value = route.query.date
  }
  if (route.query.scope) {
    currentScope.value = route.query.scope
  }
  if (route.query.repository) {
    selectedRepos.value = route.query.repository.split(',').map(s => s.trim()).filter(Boolean)
  }
  if (route.query.project) {
    selectedProjects.value = route.query.project.split(',').map(s => s.trim()).filter(Boolean)
  }
  if (route.query.branch) {
    selectedBranches.value = route.query.branch.split(',').map(s => s.trim()).filter(Boolean)
  } else {
    const savedBranch = localStorage.getItem('dev_workbench_selected_branch')
    if (savedBranch) {
      selectedBranches.value = savedBranch.split(',').map(s => s.trim()).filter(Boolean)
    }
  }
  if (route.query.member) {
    selectedMembers.value = route.query.member.split(',').map(s => s.trim()).filter(Boolean)
  }
  window.addEventListener('dev_workbench_scope_changed', handleScopeChanged)
  window.addEventListener('dev_workbench_branch_changed', handleBranchChanged)
  window.addEventListener('dev_workbench_refreshed', handleRefreshed)
  fetchData()
  checkTokenStatus()
})

onUnmounted(() => {
  window.removeEventListener('dev_workbench_scope_changed', handleScopeChanged)
  window.removeEventListener('dev_workbench_branch_changed', handleBranchChanged)
  window.removeEventListener('dev_workbench_refreshed', handleRefreshed)
})
</script>

<style scoped>
.filter-panel {
  background: #ffffff;
  padding: 14px 20px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  margin-bottom: 20px;
}

.filter-row-container {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 16px;
}

.filter-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  flex-shrink: 0;
}

.filter-label {
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

.filter-select-box {
  min-width: 140px;
  max-width: 220px;
}

.filter-actions-right {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
  flex-shrink: 0;
}

.mode-tabs {
  display: inline-flex;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 6px;
}

.btn-group-chips {
  display: inline-flex;
  gap: 6px;
}

.date-sep {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.btn-reset {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 5px 10px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}

.btn-reset:hover {
  background: #fee2e2;
  color: #b91c1c;
}

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

.mode-tab {
  padding: 4px 10px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.82rem;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.mode-tab.active {
  background: #fff;
  color: var(--primary);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}

.btn-chip {
  padding: 4px 10px;
  background: #f1f5f9;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-chip:hover {
  background: #e2e8f0;
  color: var(--text-primary);
}

.scope-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.84rem;
  color: var(--text-secondary);
  background: #f8fafc;
  padding: 6px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle);
}

.scope-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
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

.badge-role {
  font-size: 0.72rem;
  padding: 1px 6px;
  border-radius: 10px;
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 600;
}

.badge-project {
  font-size: 0.75rem;
  padding: 2px 7px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.badge-count {
  display: inline-block;
  font-weight: 700;
  font-size: 0.88rem;
  color: var(--primary);
  background: #eff6ff;
  padding: 3px 10px;
  border-radius: 12px;
}

.badge-warn {
  font-size: 0.7rem;
  color: #d97706;
  background: #fef3c7;
  padding: 1px 4px;
  border-radius: 3px;
}

.summary-box {
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 3px solid var(--primary);
  font-size: 0.85rem;
  line-height: 1.45;
}

.commit-sha {
  font-family: monospace;
  font-size: 0.78rem;
  padding: 2px 6px;
  background: #f1f5f9;
  color: #334155;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

.table-row:hover {
  background: #f8fafc;
}

.expanded-row {
  background: #f1f5f9 !important;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Keep evaluation controls readable as the workspace changes width. */
.filter-panel{padding:18px 20px;box-shadow:none}.filter-row-container{gap:15px 20px}.filter-label{font-size:12px;font-weight:500;color:var(--text-secondary)}.filter-select-box{min-width:135px}.filter-item{max-width:100%}.activity-table{min-width:1040px}.activity-table th{font-size:12px;white-space:nowrap}.summary-box{border-left:0;background:transparent;padding:0;color:var(--text-secondary);font-size:13px;line-height:1.8}.badge-count{font-size:13px;background:#f0edff;border-radius:5px;padding:3px 9px}.table-row:hover{background:#fbfbfe}.badge-project{font-size:11px;padding:2px 6px;border:0}.btn-reset{background:transparent;border-color:var(--border-subtle);color:var(--text-secondary);font-size:11px}.filter-actions-right{margin-left:auto}.scope-tag{font-size:11px;background:transparent;border:0;padding:0}.table-card{box-shadow:none!important}.form-input-sm{font-size:12px;min-height:34px}.mode-tab{font-size:12px;padding:6px 11px}.btn-chip{font-size:11px;border-radius:5px}.filter-panel .btn-primary{font-size:12px}
@media(max-width:650px){.filter-panel{padding:15px}.filter-row-container{gap:14px}.filter-item{flex-wrap:wrap;white-space:normal;min-width:0}.filter-item input{max-width:100%;min-width:0}.filter-item:nth-child(n+3){flex:1 1 42%}.filter-select-box{flex:1;min-width:0}.filter-actions-right{width:100%;justify-content:flex-end;margin-left:0}.date-sep{font-size:11px}.btn-group-chips{flex-wrap:wrap}}
</style>
