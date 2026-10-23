<template>
  <div class="sidebar-content">
    <router-link class="sidebar-brand" to="/dashboard/daily-activity" @click="$emit('navigate')"><span class="sidebar-mark"><WorkbenchIcon name="branch" :size="23" /></span><span><strong>研发工作台</strong><small>工作量评估与代码质量</small></span></router-link>
    <nav aria-label="主要导航" class="sidebar-groups">
      <div v-for="group in groups" :key="group.label" class="sidebar-group"><h2>{{ group.label }}</h2><router-link v-for="item in group.items" :key="item.path" :to="item.path" class="sidebar-link" :class="{ 'is-active': item.path === '/dashboard/code-review' && route.path.startsWith('/dashboard/code-review/') }" active-class="is-active" @click="$emit('navigate')"><WorkbenchIcon :name="item.icon" /><span>{{ item.label }}</span></router-link></div>
    </nav>
    <div class="sidebar-foot"><WorkbenchIcon name="shield" :size="17" /><span>私有审查 · 人工复核<small>结果不向仓库同步</small></span></div>
  </div>
</template>
<script setup>
import WorkbenchIcon from './WorkbenchIcon.vue'
import { useRoute } from 'vue-router'
const route = useRoute()
defineEmits(['navigate'])
const groups = [
  { label: '工作量评估', items: [
    { path: '/dashboard/daily-activity', label: '成员工作量', icon: 'activity' },
    { path: '/dashboard/project-trend', label: '项目活跃度', icon: 'trend' },
    { path: '/dashboard/absence-activity', label: '缺勤跟进', icon: 'calendar' },
    { path: '/dashboard/report-archive', label: '日报归档', icon: 'archive' },
  ] },
  { label: '代码质量', items: [{ path: '/dashboard/code-review', label: '代码审查', icon: 'code' }] },
  { label: '管理配置', items: [
    { path: '/projects', label: '项目管理', icon: 'folder' },
    { path: '/members', label: '成员管理', icon: 'members' },
    { path: '/repositories', label: '代码仓库', icon: 'repository' },
    { path: '/exemptions', label: '请假豁免', icon: 'calendar' },
  ] },
]
</script>
