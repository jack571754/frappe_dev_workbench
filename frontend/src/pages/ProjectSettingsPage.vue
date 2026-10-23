<template>
  <div class="project-settings-page" id="project-settings-page">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
      <div>
        <h2 style="font-size: 1.4rem; font-weight: 700; color: var(--text-primary);">项目配置</h2>
        <p style="font-size: 0.88rem; color: var(--text-secondary); margin-top: 4px;">
          管理团队业务交付项目，将多个 Codeup 代码仓库纳入同一项目进行统一提交统计与活跃度分析
        </p>
      </div>
      <a href="/app/project" target="_blank" class="btn-primary" id="btn-create-project-desk">
        + 在 Desk 中新建/编辑项目
      </a>
    </div>

    <!-- Projects List -->
    <div style="background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 18px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
        <h3 style="font-size: 1.05rem; font-weight: 700;">项目列表 ({{ projects.length }})</h3>
      </div>

      <div v-if="projects.length === 0" style="padding: 48px; text-align: center; color: var(--text-muted);">
        暂无项目，请点击右上角按钮在 Desk 中新建项目并关联代码库
      </div>

      <div v-else style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 0.82rem; text-transform: uppercase;">
              <th style="padding: 12px 24px;">项目名称</th>
              <th style="padding: 12px 16px;">项目描述</th>
              <th style="padding: 12px 16px;">包含代码仓库</th>
              <th style="padding: 12px 16px;">状态</th>
              <th style="padding: 12px 24px; text-align: right;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in projects" :key="p.name" style="border-bottom: 1px solid #f1f5f9;">
              <td style="padding: 14px 24px; font-weight: 600; color: var(--text-primary);">
                {{ p.project_name || p.name }}
              </td>
              <td style="padding: 14px 16px; color: var(--text-secondary);">
                {{ p.description || '-' }}
              </td>
              <td style="padding: 14px 16px;">
                <div v-if="p.project_repositories && p.project_repositories.length" style="display: flex; flex-wrap: wrap; gap: 4px; max-width: 380px;">
                  <span
                    v-for="r in p.project_repositories"
                    :key="r.repository || r.name"
                    style="background: #eef2ff; color: #4338ca; padding: 2px 8px; border-radius: 4px; font-weight: 500; font-size: 0.78rem; border: 1px solid #c7d2fe; display: inline-flex; align-items: center; gap: 3px;"
                  >
                    📦 {{ r.repository }}
                  </span>
                </div>
                <span v-else style="color: var(--text-muted); font-size: 0.8rem;">未关联代码库</span>
              </td>
              <td style="padding: 14px 16px;">
                <span v-if="p.is_active" style="background: #ecfdf5; color: #047857; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem;">启用中</span>
                <span v-else style="background: #f1f5f9; color: #94a3b8; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem;">已禁用</span>
              </td>
              <td style="padding: 14px 24px; text-align: right;">
                <a :href="`/app/project/${p.name}`" target="_blank" class="btn-secondary" style="padding: 4px 10px; font-size: 0.78rem;">
                  配置与仓库
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

const projects = ref([])

onMounted(async () => {
  try {
    const res = await request('/api/resource/Project?fields=["name","project_name","description","is_active"]&limit_page_length=50')
    const data = await res.json()
    projects.value = data.data || []

    for (let p of projects.value) {
      try {
        const detailRes = await request(`/api/resource/Project/${encodeURIComponent(p.name)}`)
        const detail = await detailRes.json()
        p.project_repositories = detail.data?.project_repositories || []
      } catch (e) {}
    }
  } catch (err) {}
})
</script>
