<template>
  <div class="project-trend-page" id="project-trend-page">
    <!-- Top Metric Summary Cards -->
    <div class="metric-grid">
      <div class="metric-card" id="metric-trend-total">
        <div>
          <div class="metric-label">{{ periodSummaryLabel }}</div>
          <div class="metric-value">
            {{ metricType === 'commits' ? formatNumber(trendSummary.total_commits || trendSummary.total_commits_12w) : formatNumber(trendSummary.total_lines) }}
            <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">{{ metricType === 'commits' ? '次' : 'lines' }}</span>
          </div>
        </div>
        <div class="metric-icon indigo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-trend-avg">
        <div>
          <div class="metric-label">{{ averageMetricLabel }}</div>
          <div class="metric-value">
            {{ metricType === 'commits' ? (trendSummary.average_commits || trendSummary.average_weekly_commits) : formatNumber(trendSummary.average_lines) }}
            <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">{{ averageUnitLabel }}</span>
          </div>
        </div>
        <div class="metric-icon emerald">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
            <polyline points="17 6 23 6 23 12"></polyline>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-trend-recent">
        <div>
          <div class="metric-label">{{ recentMetricLabel }}</div>
          <div class="metric-value">
            {{ formatNumber(trendSummary.recent_commits || trendSummary.recent_3w_commits) }}
            <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-muted);">次</span>
          </div>
        </div>
        <div class="metric-icon amber">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
        </div>
      </div>

      <div class="metric-card" id="metric-trend-direction">
        <div>
          <div class="metric-label">近期研发活跃动能</div>
          <div class="metric-value" style="display: flex; align-items: center; gap: 8px;">
            <span v-if="trendSummary.trend === 'up'" style="color: #059669;">持续加速 ↗</span>
            <span v-else-if="trendSummary.trend === 'down'" style="color: #ea580c;">放缓下行 ↘</span>
            <span v-else style="color: #2563eb;">平稳推进 →</span>
          </div>
        </div>
        <div class="metric-icon" :style="trendSummary.trend === 'up' ? 'background: #ecfdf5; color: #059669;' : 'background: #eff6ff; color: #2563eb;'">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
        </div>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filter-panel" style="background: #fff; padding: 16px 20px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); margin-bottom: 20px;">
      <div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px;">
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 14px;">
          <!-- Time Granularity Filter (Day / Week / Month) -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">时间粒度：</label>
            <div style="display: flex; background: #f1f5f9; padding: 3px; border-radius: 6px;">
              <button
                id="btn-granularity-day"
                type="button"
                :class="['mode-tab', currentInterval === 'day' ? 'active' : '']"
                @click="setIntervalMode('day')"
              >
                按天 (近30天)
              </button>
              <button
                id="btn-granularity-week"
                type="button"
                :class="['mode-tab', currentInterval === 'week' ? 'active' : '']"
                @click="setIntervalMode('week')"
              >
                按周 (过去12周)
              </button>
              <button
                id="btn-granularity-month"
                type="button"
                :class="['mode-tab', currentInterval === 'month' ? 'active' : '']"
                @click="setIntervalMode('month')"
              >
                按月 (过去12个月)
              </button>
            </div>
          </div>

          <!-- Branch Scope Quick Toggle (全部分支 / 仅默认分支) -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">分支统计：</label>
            <div style="display: flex; background: #f1f5f9; padding: 3px; border-radius: 6px;">
              <button
                id="btn-scope-all"
                type="button"
                :class="['mode-tab', currentScope === 'all' ? 'active' : '']"
                @click="setScope('all')"
              >
                全部分支
              </button>
              <button
                id="btn-scope-default"
                type="button"
                :class="['mode-tab', currentScope === 'default' ? 'active' : '']"
                @click="setScope('default')"
              >
                仅默认分支
              </button>
            </div>
          </div>

          <!-- Project MultiSelect -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary); white-space: nowrap;">对标项目：</label>
            <div id="filter-trend-project" style="min-width: 170px; max-width: 260px;">
              <MultiSelect
                v-model="selectedProjects"
                :options="projectOptions"
                placeholder="全部项目 (横向对比)"
                @update:modelValue="fetchTrendData"
              />
            </div>
          </div>

          <!-- Repository MultiSelect -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary); white-space: nowrap;">代码仓库：</label>
            <div id="filter-trend-repository" style="min-width: 160px; max-width: 250px;">
              <MultiSelect
                v-model="selectedRepos"
                :options="repoOptions"
                placeholder="全部代码仓库"
                @update:modelValue="fetchTrendData"
              />
            </div>
          </div>

          <!-- Member MultiSelect -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary); white-space: nowrap;">个人聚焦：</label>
            <div id="filter-trend-member" style="min-width: 150px; max-width: 240px;">
              <MultiSelect
                v-model="selectedMembers"
                :options="memberOptions"
                placeholder="全部成员"
                @update:modelValue="fetchTrendData"
              />
            </div>
          </div>

          <!-- Reset Filters Button -->
          <button
            v-if="hasActiveTrendFilters"
            id="btn-trend-reset-filters"
            type="button"
            class="btn-chip"
            style="background: #f1f5f9; color: #475569; border: 1px solid var(--border-medium); font-size: 0.8rem; padding: 4px 10px; cursor: pointer; border-radius: 6px; white-space: nowrap;"
            @click="resetTrendFilters"
            title="清空并重置所有多选筛选条件"
          >
            重置筛选 ✕
          </button>

          <!-- Metric Display Mode -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-secondary);">统计指标：</label>
            <div style="display: flex; background: #f1f5f9; padding: 3px; border-radius: 6px;">
              <button
                id="btn-metric-commits"
                type="button"
                :class="['mode-tab', metricType === 'commits' ? 'active' : '']"
                @click="metricType = 'commits'"
              >
                提交次数
              </button>
              <button
                id="btn-metric-lines"
                type="button"
                :class="['mode-tab', metricType === 'lines' ? 'active' : '']"
                @click="metricType = 'lines'"
              >
                变更代码 (行)
              </button>
            </div>
          </div>
        </div>

        <!-- Refresh -->
        <div style="display: flex; align-items: center; gap: 12px;">
          <button
            type="button"
            class="btn-secondary"
            style="padding: 7px 14px; font-size: 0.86rem; display: flex; align-items: center; gap: 6px;"
            @click="fetchTrendData"
          >
            <span>🔄 刷新走势</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Chart Card -->
    <div class="chart-card" style="background: #fff; padding: 24px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); margin-bottom: 24px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
            <span>📈 {{ chartTitleText }}</span>
            <span style="font-size: 0.8rem; font-weight: 600; color: #4338ca; background: #e0e7ff; padding: 2px 8px; border-radius: 12px;">
              {{ currentScope === 'all' ? '全部分支' : '仅默认分支' }}
            </span>
            <span style="font-size: 0.8rem; font-weight: 500; color: #047857; background: #ecfdf5; padding: 2px 8px; border-radius: 12px;">
              {{ currentInterval === 'day' ? '按天走势' : (currentInterval === 'month' ? '按月走势' : '过去12周') }}
            </span>
          </div>
          <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 4px;">
            基于 Frappe UI Charts 规范设计，支持点击图例隐藏/显示系列、对比虚线、周均/日均/月均参考线与明细悬浮提示
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 0.82rem; color: var(--text-secondary); background: #f8fafc; padding: 5px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
            当前指标: <strong>{{ metricType === 'commits' ? '代码提交 (次)' : '变更代码 (行)' }}</strong>
          </span>
        </div>
      </div>

      <!-- Frappe UI LineChart Component with Interactive DataPoint Click -->
      <LineChart
        :data="chartData"
        x="week"
        :y="chartSeriesKeys"
        :series-config="chartSeriesConfig"
        :reference-lines="referenceLines"
        :tooltip-columns="tooltipColumns"
        :loading="loading"
        :smooth="true"
        :show-data-points="true"
        :connect-nulls="true"
        :x-axis="{ title: xAxisTitle }"
        :y-axis="{ title: metricType === 'commits' ? '代码提交 (次)' : '变更代码 (行)' }"
        v-model:hidden-series="hiddenSeries"
        @datapoint-click="handleDatapointClick"
        height="330px"
      />
    </div>

    <!-- Quick Daily Data Inspector Strip -->
    <div style="background: #ffffff; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); margin-bottom: 24px; overflow: hidden;">
      <div style="padding: 14px 20px; background: #f8fafc; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 0.88rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
            <span>📅 每天数据速查：</span>
          </span>
          <select
            v-model="quickSelectedDayIndex"
            class="form-input-sm"
            style="min-width: 220px;"
            @change="openDayDetailByIndex(quickSelectedDayIndex)"
          >
            <option v-for="(lbl, idx) in labelsList" :key="idx" :value="idx">
              {{ lbl }} ({{ weekLabels[idx] }})
            </option>
          </select>
          <button
            type="button"
            class="btn-primary"
            style="padding: 6px 14px; font-size: 0.82rem;"
            @click="openDayDetailByIndex(quickSelectedDayIndex)"
          >
            查看该天详细数据
          </button>
        </div>

        <div style="font-size: 0.8rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
          <span>💡 提示: 点击图表任意数据点或下方表头，均可直接弹窗查看该天全部提交与成员明细</span>
        </div>
      </div>
    </div>

    <!-- Data Breakdown Table -->
    <div class="table-card" style="background: #fff; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); font-size: 0.95rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; justify-content: space-between;">
        <span>📊 {{ tableTitleText }}</span>
        <span style="font-size: 0.8rem; font-weight: normal; color: var(--text-muted);">
          * 点击具体日期表头可直接下钻查看该天提交明细；在图例点击项目系列可联动隐藏
        </span>
      </div>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 1px solid var(--border-medium); color: var(--text-secondary);">
              <th style="padding: 12px 18px; width: 220px; position: sticky; left: 0; background: #f8fafc; z-index: 1;">对标对象 / 项目与代码仓库</th>
              <th
                v-for="(w, idx) in weekLabels"
                :key="idx"
                style="padding: 10px 12px; text-align: center; white-space: nowrap; cursor: pointer; transition: background 0.15s;"
                class="hover-cell-header"
                @click="openDayDetailByIndex(idx)"
                :title="`点击查看 ${labelsList[idx] || w} 的每天明细数据`"
              >
                <div style="display: flex; flex-direction: column; align-items: center; gap: 2px;">
                  <span style="font-weight: 600;">{{ w }}</span>
                  <span style="font-size: 0.68rem; color: #6366f1; font-weight: normal;">查看</span>
                </div>
              </th>
              <th style="padding: 12px 18px; text-align: right; width: 120px; position: sticky; right: 0; background: #f8fafc; z-index: 1;">
                {{ tableTotalColumnLabel }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(s, idx) in seriesList"
              :key="s.name"
              style="border-bottom: 1px solid var(--border-subtle); transition: opacity 0.2s;"
              :style="{ opacity: hiddenSeries.includes(s.name) ? 0.35 : 1 }"
            >
              <td style="padding: 12px 18px; font-weight: 600; display: flex; align-items: center; gap: 10px; position: sticky; left: 0; background: #fff; z-index: 1;">
                <span class="legend-color-dot" :style="{ backgroundColor: getColor(idx, s.is_total) }"></span>
                <div>
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span :style="{ textDecoration: hiddenSeries.includes(s.name) ? 'line-through' : 'none' }">{{ s.project_name || s.name }}</span>
                    <span v-if="s.is_total" style="font-size: 0.72rem; padding: 1px 6px; border-radius: 4px; background: #e2e8f0; color: #475569;">
                      对比线
                    </span>
                  </div>
                  <div v-if="s.repositories && s.repositories.length" style="font-size: 0.75rem; color: #4338ca; font-weight: normal; margin-top: 3px; display: flex; align-items: center; gap: 4px;">
                    <span style="padding: 1px 6px; border-radius: 3px; background: #eef2ff; color: #4338ca;">
                      📦 {{ s.repositories.join(', ') }}
                    </span>
                  </div>
                </div>
              </td>
              <td
                v-for="(val, pIdx) in getSeriesValues(s)"
                :key="pIdx"
                style="padding: 10px 12px; text-align: center; white-space: nowrap; cursor: pointer;"
                :style="val > 0 ? 'font-weight: 600; color: var(--text-primary);' : 'color: var(--text-muted);'"
                @click="openDayDetailByIndex(pIdx)"
                :title="`点击查看该日数据明细`"
              >
                {{ formatNumber(val) }}
              </td>
              <td style="padding: 12px 18px; text-align: right; font-weight: 700; color: var(--primary); position: sticky; right: 0; background: #fff; z-index: 1;">
                {{ formatNumber(getSeriesValues(s).reduce((a, b) => a + b, 0)) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Daily Data Detail Modal (查看每天数据明细) -->
    <div
      v-if="selectedDayDetail"
      class="modal-backdrop"
      style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(3px); display: flex; align-items: center; justify-content: center; z-index: 10000;"
      @click.self="selectedDayDetail = null"
    >
      <div
        class="modal-card"
        style="background: #ffffff; border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); width: 92%; max-width: 780px; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; animation: modalIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);"
      >
        <!-- Modal Header -->
        <div style="padding: 20px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h3 style="font-size: 1.2rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 10px;">
              <span>📅 {{ selectedDayDetail.full_label || selectedDayDetail.date }} 数据明细</span>
              <span style="font-size: 0.76rem; font-weight: 600; padding: 2px 8px; border-radius: 9999px; background: #e0e7ff; color: #4338ca;">
                {{ currentScope === 'all' ? '全部分支' : '仅默认分支' }}
              </span>
            </h3>
            <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 4px;">
              日期: {{ selectedDayDetail.date }} · 查看当天所有活跃成员、提交次数与变更代码行数
            </p>
          </div>
          <button
            type="button"
            class="btn-secondary"
            style="padding: 4px 10px; font-size: 0.82rem;"
            @click="selectedDayDetail = null"
          >
            ✕ 关闭
          </button>
        </div>

        <!-- Modal Body -->
        <div style="padding: 20px 24px; overflow-y: auto; flex: 1;">
          <!-- Day Summary Metrics -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 14px; margin-bottom: 22px;">
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px;">
              <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 4px;">当日提交总次数</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #4f46e5;">
                {{ selectedDayDetail.total_commits || 0 }} <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-muted);">次</span>
              </div>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px;">
              <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 4px;">当日变更代码行数</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #059669;">
                {{ formatNumber(selectedDayDetail.total_lines || 0) }} <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-muted);">lines</span>
              </div>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px;">
              <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 4px;">当日活跃提交成员</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: var(--text-primary);">
                {{ (selectedDayDetail.members || []).length }} <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-muted);">人</span>
              </div>
            </div>
          </div>

          <!-- Loading Indicator -->
          <div v-if="loadingDayDetail" style="padding: 40px; text-align: center; color: var(--text-muted);">
            正在拉取该日活动明细...
          </div>

          <!-- Members Contributions List -->
          <div v-else-if="selectedDayDetail.members && selectedDayDetail.members.length">
            <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">
              当日提交开发者贡献列表 ({{ selectedDayDetail.members.length }})
            </h4>

            <div style="display: flex; flex-direction: column; gap: 10px;">
              <div
                v-for="m in selectedDayDetail.members"
                :key="m.member || m.member_name"
                style="border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px 16px; background: #ffffff;"
              >
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                  <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background: #e0e7ff; color: #4338ca; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.82rem;">
                      {{ (m.member_name || m.member || 'U').slice(0, 1).toUpperCase() }}
                    </div>
                    <div>
                      <div style="font-weight: 700; color: var(--text-primary); font-size: 0.92rem;">
                        {{ m.member_name || m.member }}
                      </div>
                      <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 3px;">
                        <span v-for="p in m.projects" :key="p" style="font-size: 0.72rem; padding: 1px 6px; border-radius: 4px; background: #f1f5f9; color: #475569;">
                          {{ p }}
                        </span>
                        <span v-for="r in m.repositories" :key="r" style="font-size: 0.72rem; padding: 1px 6px; border-radius: 4px; background: #eef2ff; color: #4338ca; font-weight: 500;">
                          📦 {{ r }}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div style="text-align: right;">
                    <div style="font-size: 0.88rem; font-weight: 700; color: #4f46e5;">
                      {{ m.commit_count }} 次提交
                    </div>
                    <div style="font-size: 0.78rem; color: #059669; margin-top: 2px;">
                      +{{ formatNumber(m.lines_added || 0) }} / -{{ formatNumber(m.lines_deleted || 0) }} (共 {{ formatNumber(m.total_lines || 0) }} 行)
                    </div>
                  </div>
                </div>

                <!-- AI Summary or Commits Preview -->
                <div v-if="m.summary" style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5; background: #f8fafc; padding: 8px 12px; border-radius: 6px; margin-top: 6px;">
                  {{ m.summary }}
                </div>
              </div>
            </div>
          </div>

          <div v-else style="padding: 40px; text-align: center; color: var(--text-muted); background: #f8fafc; border-radius: 8px;">
            该日期无任何代码提交记录
          </div>
        </div>

        <!-- Modal Footer -->
        <div style="padding: 16px 24px; border-top: 1px solid var(--border-subtle); background: #f8fafc; display: flex; justify-content: space-between; align-items: center;">
          <router-link
            :to="`/dashboard/daily-activity?date=${selectedDayDetail.date}&scope=${currentScope}${selectedRepos.length ? '&repository=' + encodeURIComponent(selectedRepos.join(',')) : ''}`"
            class="btn-primary"
            style="padding: 7px 18px; font-size: 0.84rem; display: flex; align-items: center; gap: 6px;"
          >
            <span>在成员日报中查看完整报告 →</span>
          </router-link>
          <button
            type="button"
            class="btn-secondary"
            style="padding: 6px 14px; font-size: 0.84rem;"
            @click="selectedDayDetail = null"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { MultiSelect } from 'frappe-ui'
import { request } from '@/utils/api'
import LineChart from '@/components/LineChart.vue'

const currentInterval = ref('day') // 'day' | 'week' | 'month' (支持按天查看)
const selectedProjects = ref([])
const selectedRepos = ref([])
const selectedMembers = ref([])
const metricType = ref('lines') // 支持查看变更代码 (行)
const currentScope = ref(localStorage.getItem('dev_workbench_branch_scope') || 'all')

const loading = ref(false)
const hiddenSeries = ref([])

const repositoriesList = ref([])
const projectsList = ref([])
const membersList = ref([])

const extractValues = (arr) => {
  if (!arr) return []
  if (!Array.isArray(arr)) return [arr].filter(Boolean)
  return arr.map(item => (typeof item === 'object' && item !== null ? item.value : item)).filter(Boolean)
}

const projectOptions = computed(() => {
  return projectsList.value.map(p => ({
    label: `${p.project_name}${p.repo_display ? ` (${p.repo_display})` : ''}`,
    value: p.name,
  }))
})

const repoOptions = computed(() => {
  return repositoriesList.value.map(r => ({
    label: `📦 ${r}`,
    value: r,
  }))
})

const memberOptions = computed(() => {
  return membersList.value.map(m => ({
    label: m.member_name,
    value: m.name,
  }))
})

const hasActiveTrendFilters = computed(() => {
  return selectedProjects.value.length > 0 || selectedRepos.value.length > 0 || selectedMembers.value.length > 0
})

const resetTrendFilters = () => {
  selectedProjects.value = []
  selectedRepos.value = []
  selectedMembers.value = []
  fetchTrendData()
}

const trendSummary = ref({
  total_commits: 0,
  total_commits_12w: 0,
  total_lines: 0,
  average_commits: 0,
  average_weekly_commits: 0,
  average_lines: 0,
  recent_commits: 0,
  recent_3w_commits: 0,
  trend: 'stable',
  benchmark_label: '日均基准: 0次/天',
  benchmark_lines_label: '日均基准: 0行/天',
})

const weekLabels = ref([])
const datesList = ref([])
const labelsList = ref([])
const seriesList = ref([])

const quickSelectedDayIndex = ref(0)
const selectedDayDetail = ref(null)
const loadingDayDetail = ref(false)

const palette = [
  '#4f46e5', // indigo
  '#059669', // emerald
  '#ea580c', // orange
  '#db2777', // pink
  '#0284c7', // light blue
  '#7c3aed', // purple
  '#d97706', // amber
  '#0d9488', // teal
]

const getColor = (idx, isTotal) => {
  if (isTotal) return '#1e293b' // slate 800
  return palette[idx % palette.length]
}

const formatNumber = (num) => {
  if (!num) return '0'
  return Number(num).toLocaleString('en-US')
}

// Dynamic Labels based on currentInterval
const periodSummaryLabel = computed(() => {
  if (currentInterval.value === 'day') return '过去 30 天累计产出'
  if (currentInterval.value === 'month') return '过去 12 个月累计产出'
  return '过去 12 周累计产出'
})

const averageMetricLabel = computed(() => {
  if (currentInterval.value === 'day') return '日均代码产出'
  if (currentInterval.value === 'month') return '月均代码产出'
  return '周均代码产出'
})

const averageUnitLabel = computed(() => {
  const metric = metricType.value === 'commits' ? '次' : '行'
  if (currentInterval.value === 'day') return `${metric}/天`
  if (currentInterval.value === 'month') return `${metric}/月`
  return `${metric}/周`
})

const recentMetricLabel = computed(() => {
  if (currentInterval.value === 'day') return '近 7 天提交总量'
  if (currentInterval.value === 'month') return '近 2 个月提交总量'
  return '近 3 周提交总量'
})

const chartTitleText = computed(() => {
  if (currentInterval.value === 'day') return '过去 30 天研发活跃度趋势折线图'
  if (currentInterval.value === 'month') return '过去 12 个月研发活跃度趋势折线图'
  return '过去 12 周研发活跃度趋势折线图'
})

const xAxisTitle = computed(() => {
  if (currentInterval.value === 'day') return '日期 (近30天)'
  if (currentInterval.value === 'month') return '月份 (过去12个月)'
  return '周期 (过去12周)'
})

const tableTitleText = computed(() => {
  if (currentInterval.value === 'day') return '过去 30 天数据明细表'
  if (currentInterval.value === 'month') return '过去 12 个月数据明细表'
  return '过去 12 周数据明细表'
})

const tableTotalColumnLabel = computed(() => {
  if (currentInterval.value === 'day') return '30天总计'
  if (currentInterval.value === 'month') return '12月总计'
  return '12周总计'
})

const getSeriesValues = (s) => {
  if (metricType.value === 'lines') {
    return s.lines || (s.commits ? s.commits.map(c => c * 50) : [])
  }
  return s.commits || []
}

// Frappe UI LineChart Data Adapters
const chartData = computed(() => {
  if (!weekLabels.value.length || !seriesList.value.length) return []
  return weekLabels.value.map((w, idx) => {
    const row = {
      week: w,
      date: datesList.value[idx] || w,
      full_label: labelsList.value[idx] || w,
    }
    let totalLines = 0
    let totalCommits = 0
    seriesList.value.forEach((s) => {
      const vals = getSeriesValues(s)
      row[s.name] = vals[idx] !== undefined ? vals[idx] : 0
      if (s.lines && s.lines[idx]) {
        totalLines += s.lines[idx]
      }
      if (s.commits && s.commits[idx]) {
        totalCommits += s.commits[idx]
      }
    })
    row.total_lines = totalLines
    row.total_commits = totalCommits
    return row
  })
})

const chartSeriesKeys = computed(() => {
  return seriesList.value.map((s) => s.name)
})

const chartSeriesConfig = computed(() => {
  const config = {}
  seriesList.value.forEach((s, idx) => {
    const isTotal = s.is_total || s.name === '总计' || s.name.includes('汇总')
    config[s.name] = {
      label: isTotal ? '全队总计 (对比线)' : s.name,
      dashed: isTotal, // Frappe UI LineChart spec: comparison series dashed
      color: getColor(idx, isTotal),
      smooth: true,
      showDataPoints: true,
      format: (val) => `${formatNumber(val)} ${metricType.value === 'commits' ? '次' : '行'}`,
    }
  })
  return config
})

// Targets and thresholds via referenceLines (周均 / 日均 / 月均参考线)
const referenceLines = computed(() => {
  if (metricType.value === 'lines') {
    const avg = trendSummary.value.average_lines || 0
    if (avg <= 0) return []
    const lbl = trendSummary.value.benchmark_lines_label || `行数基准: ${formatNumber(avg)}行`
    return [
      {
        value: avg,
        axis: 'y',
        label: lbl,
        color: '#059669', // emerald for code lines
        dashed: true,
      },
    ]
  } else {
    const avg = trendSummary.value.average_commits || trendSummary.value.average_weekly_commits || 0
    if (avg <= 0) return []
    const lbl = trendSummary.value.benchmark_label || `提交基准: ${avg}次`
    return [
      {
        value: avg,
        axis: 'y',
        label: lbl,
        color: '#94a3b8',
        dashed: true,
      },
    ]
  }
})

// Context in the tooltip via tooltipColumns
const tooltipColumns = computed(() => {
  const periodDesc = currentInterval.value === 'day' ? '当日' : (currentInterval.value === 'month' ? '当月' : '当周')
  if (metricType.value === 'lines') {
    return [
      {
        name: 'total_commits',
        label: `${periodDesc}提交总数`,
        format: (val) => `${val || 0} 次`,
      },
      {
        name: 'action_hint',
        label: '交互提示',
        format: () => '👉 点击数据点查看每天详细数据',
      },
    ]
  } else {
    return [
      {
        name: 'total_lines',
        label: `${periodDesc}变更代码`,
        format: (val) => `${formatNumber(val)} 行`,
      },
      {
        name: 'action_hint',
        label: '交互提示',
        format: () => '👉 点击数据点查看每天详细数据',
      },
    ]
  }
})

const setIntervalMode = (mode) => {
  currentInterval.value = mode
  fetchTrendData()
}

const setScope = (scope) => {
  currentScope.value = scope
  localStorage.setItem('dev_workbench_branch_scope', scope)
  window.dispatchEvent(new CustomEvent('dev_workbench_scope_changed', { detail: { scope } }))
  fetchTrendData()
}

const fetchTrendData = async () => {
  loading.value = true
  try {
    const pValues = extractValues(selectedProjects.value)
    const pParam = pValues.length > 0 ? pValues.join(',') : 'all'
    let url = `/api/method/dev_workbench.api.v1.activity.get_project_trend?project_id=${encodeURIComponent(pParam)}&interval=${encodeURIComponent(currentInterval.value)}&scope=${encodeURIComponent(currentScope.value)}`

    const mValues = extractValues(selectedMembers.value)
    if (mValues.length > 0) {
      url += `&member_id=${encodeURIComponent(mValues.join(','))}`
    }
    const rValues = extractValues(selectedRepos.value)
    if (rValues.length > 0) {
      url += `&repository=${encodeURIComponent(rValues.join(','))}`
    }

    const res = await request(url)
    const json = await res.json()
    const data = json.message || json

    weekLabels.value = data.weeks || data.periods || []
    datesList.value = data.dates || []
    labelsList.value = data.labels || []
    seriesList.value = data.series || []

    if (data.repositories && data.repositories.length) {
      const merged = new Set([...repositoriesList.value, ...data.repositories])
      repositoriesList.value = Array.from(merged).sort()
    }

    trendSummary.value = data.summary || {
      total_commits: 0,
      total_commits_12w: 0,
      total_lines: 0,
      average_commits: 0,
      average_weekly_commits: 0,
      average_lines: 0,
      recent_commits: 0,
      recent_3w_commits: 0,
      trend: 'stable',
      benchmark_label: '日均基准: 0次/天',
      benchmark_lines_label: '日均基准: 0行/天',
    }

    if (labelsList.value.length > 0) {
      quickSelectedDayIndex.value = labelsList.value.length - 1
    }
  } catch (err) {
    console.error('获取项目趋势异常:', err)
  } finally {
    loading.value = false
  }
}

const fetchFilterOptions = async () => {
  try {
    const pRes = await request('/api/resource/Project?fields=["name","project_name"]&limit_page_length=0')
    const pJson = await pRes.json()
    const pData = pJson.data || []

    const repoItemRes = await request('/api/resource/Project Repository Item?fields=["parent","repository"]&limit_page_length=0')
    const repoItemJson = await repoItemRes.json()
    const repoItems = repoItemJson.data || []

    const pRepoMap = {}
    const repoSet = new Set()
    for (const item of repoItems) {
      if (!pRepoMap[item.parent]) pRepoMap[item.parent] = []
      if (item.repository) {
        pRepoMap[item.parent].push(item.repository)
        repoSet.add(item.repository)
      }
    }

    for (const p of pData) {
      const repos = pRepoMap[p.name] || []
      p.repositories = repos
      if (repos.length === 1) {
        p.repo_display = repos[0]
      } else if (repos.length > 1) {
        p.repo_display = `${repos[0]} 等${repos.length}个仓库`
      } else {
        p.repo_display = ''
      }
    }

    projectsList.value = pData
    if (repoSet.size > 0) {
      repositoriesList.value = Array.from(repoSet).sort()
    }

    const mRes = await request('/api/resource/Project Member?fields=["name","member_name"]&filters=[["is_active","=",1]]')
    const mJson = await mRes.json()
    membersList.value = mJson.data || []
  } catch (e) {
    console.error('加载项目与成员选项失败:', e)
  }
}

// 每天数据明细下钻与弹窗
const openDayDetailByIndex = async (idx) => {
  if (idx === undefined || idx === null || idx < 0) return
  const date = datesList.value[idx] || weekLabels.value[idx]
  const fullLabel = labelsList.value[idx] || weekLabels.value[idx]

  selectedDayDetail.value = {
    date,
    full_label: fullLabel,
    total_commits: 0,
    total_lines: 0,
    members: [],
  }
  loadingDayDetail.value = true

  try {
		let detailUrl = `/api/method/dev_workbench.api.v1.activity.get_daily_overview?date=${encodeURIComponent(date)}&scope=${encodeURIComponent(currentScope.value)}`
    if (selectedRepoName.value) {
      detailUrl += `&repository=${encodeURIComponent(selectedRepoName.value)}`
    }
    if (selectedProjectId.value && selectedProjectId.value !== 'all') {
      const proj = projectsList.value.find(p => p.name === selectedProjectId.value)
      if (proj) {
        detailUrl += `&project=${encodeURIComponent(proj.project_name || proj.name)}`
      }
    }

    const res = await request(detailUrl)
    const json = await res.json()
    const data = json.message || json

    selectedDayDetail.value = {
      date,
      full_label: fullLabel,
      total_commits: data.metrics?.total_commits || 0,
      total_lines: data.metrics?.total_lines || 0,
      members: data.members || [],
    }
  } catch (e) {
    console.error('加载单日明细失败:', e)
  } finally {
    loadingDayDetail.value = false
  }
}

const handleDatapointClick = (event) => {
  if (event && event.dataIndex !== undefined) {
    openDayDetailByIndex(event.dataIndex)
  }
}

const handleScopeChanged = (e) => {
  currentScope.value = e.detail?.scope || 'all'
  fetchTrendData()
}

onMounted(() => {
  window.addEventListener('dev_workbench_scope_changed', handleScopeChanged)
  fetchFilterOptions()
  fetchTrendData()
})

onUnmounted(() => {
  window.removeEventListener('dev_workbench_scope_changed', handleScopeChanged)
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

.legend-color-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.hover-cell-header:hover {
  background: #eef2ff !important;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
