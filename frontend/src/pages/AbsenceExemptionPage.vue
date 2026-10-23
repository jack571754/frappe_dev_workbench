<template>
  <div class="absence-exemption-page" id="absence-exemption-page">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
      <div>
        <h2 style="font-size: 1.4rem; font-weight: 700; color: var(--text-primary);">请假与非编码豁免管理</h2>
        <p style="font-size: 0.88rem; color: var(--text-secondary); margin-top: 4px;">
          在此登记团队成员的请假或出差日期，处于豁免期内的人员不会被判定为缺勤
        </p>
      </div>
      <a href="/app/absence-exemption/new" target="_blank" class="btn-primary">
        + 在 Desk 中登记豁免
      </a>
    </div>

    <!-- Exemptions List -->
    <div style="background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 18px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
        <h3 style="font-size: 1.05rem; font-weight: 700;">豁免记录 ({{ exemptions.length }})</h3>
      </div>

      <div v-if="exemptions.length === 0" style="padding: 48px; text-align: center; color: var(--text-muted);">
        暂无请假豁免记录
      </div>

      <div v-else style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 0.82rem; text-transform: uppercase;">
              <th style="padding: 12px 24px;">成员姓名</th>
              <th style="padding: 12px 16px;">开始日期</th>
              <th style="padding: 12px 16px;">结束日期</th>
              <th style="padding: 12px 16px;">豁免原因</th>
              <th style="padding: 12px 16px;">状态</th>
              <th style="padding: 12px 24px; text-align: right;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in exemptions" :key="e.name" style="border-bottom: 1px solid #f1f5f9;">
              <td style="padding: 14px 24px; font-weight: 600; color: var(--text-primary);">
                {{ e.member_name || e.member }}
              </td>
              <td style="padding: 14px 16px; font-family: var(--font-mono); font-size: 0.85rem;">
                {{ e.start_date }}
              </td>
              <td style="padding: 14px 16px; font-family: var(--font-mono); font-size: 0.85rem;">
                {{ e.end_date }}
              </td>
              <td style="padding: 14px 16px; color: var(--text-secondary);">
                {{ e.reason }}
              </td>
              <td style="padding: 14px 16px;">
                <span v-if="e.is_active" style="background: #ecfdf5; color: #047857; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem;">有效</span>
                <span v-else style="background: #f1f5f9; color: #94a3b8; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem;">已失效</span>
              </td>
              <td style="padding: 14px 24px; text-align: right;">
                <a :href="`/app/absence-exemption/${e.name}`" target="_blank" class="btn-secondary" style="padding: 4px 10px; font-size: 0.78rem;">
                  编辑
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { request } from '@/utils/api'

const exemptions = ref([])

onMounted(async () => {
  try {
    const res = await request('/api/resource/Absence Exemption?fields=["name","member","member_name","start_date","end_date","reason","is_active"]&limit_page_length=50')
    const data = await res.json()
    exemptions.value = data.data || []
  } catch (err) {}
})
</script>
