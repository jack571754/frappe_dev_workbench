<template>
  <header class="workspace-topbar">
    <div class="topbar-location"><button class="mobile-menu-button" aria-label="打开导航菜单" @click="$emit('open-navigation')"><WorkbenchIcon name="menu" /></button><span class="topbar-parent">{{ section }}</span><span class="breadcrumb-divider">/</span><strong>{{ title }}</strong></div>
    <div class="topbar-actions"><button class="sync-button" :disabled="isSyncing" @click="handleTriggerSync"><WorkbenchIcon name="refresh" :size="16" :class="{ 'is-spinning': isSyncing }" /><span>{{ isSyncing ? '同步中…' : '同步提交数据' }}</span></button><span class="topbar-rule" /><div class="topbar-user"><span class="profile-avatar">{{ userInitial }}</span><span>{{ userName }}</span></div><button v-if="isInIframe" class="desk-link" @click="openInNewTab">全屏打开</button><a v-else href="/app" target="_top" class="desk-link">返回 Desk</a></div>
  </header>
  <div v-if="toastMessage" class="workspace-toast" role="status">{{ toastMessage }}</div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/utils/api'
import WorkbenchIcon from './WorkbenchIcon.vue'
defineEmits(['open-navigation'])
const route = useRoute(), isInIframe = ref(false), isSyncing = ref(false), toastMessage = ref('')
const title = computed(() => ({ DailyActivity: '成员工作量', ProjectTrend: '项目活跃度', AbsenceActivity: '缺勤跟进', ReportArchive: '日报归档', CodeReview: '审查任务', CodeReviewDetail: '审查详情', Projects: '项目管理', Members: '成员管理', Repositories: '代码仓库', Exemptions: '请假豁免' }[route.name] || '工作台'))
const section = computed(() => route.path.includes('code-review') ? '代码质量' : route.path.startsWith('/dashboard') ? '工作量评估' : '管理配置')
const userName = computed(() => window.boot?.user_fullname || window.boot?.user || '管理员')
const userInitial = computed(() => userName.value.slice(0, 1).toUpperCase())
let toastTimer
onMounted(() => { try { isInIframe.value = window.self !== window.top } catch { isInIframe.value = true } })
onUnmounted(() => clearTimeout(toastTimer))
function openInNewTab() { window.open(window.location.href, '_blank', 'noopener') }
function showToast(msg) { toastMessage.value = msg; clearTimeout(toastTimer); toastTimer = setTimeout(() => { toastMessage.value = '' }, 5000) }
async function handleTriggerSync() {
  if (isSyncing.value) return
  isSyncing.value = true
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.sync.trigger_sync', {})
    const data = await res.json()
    if (res.ok && data.message?.status === 'success') { showToast(data.message.message || '提交数据已同步'); window.dispatchEvent(new CustomEvent('dev_workbench_refreshed', { detail: data.message })) }
    else showToast(data.message?.message || '同步失败，请检查仓库配置')
  } catch { showToast('连接失败，请稍后重试') } finally { isSyncing.value = false }
}
</script>
