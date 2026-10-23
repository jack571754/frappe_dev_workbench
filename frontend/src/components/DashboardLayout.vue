<template>
  <div class="dashboard-layout">
    <header v-if="!isReview" class="workspace-page-heading"><div><h1>{{ heading.title }}</h1><p>{{ heading.description }}</p></div><router-link v-if="route.name === 'DailyActivity'" to="/dashboard/code-review" class="btn-secondary"><WorkbenchIcon name="code" :size="16" />查看代码审查</router-link></header>
    <WorkloadScopeBar v-if="['DailyActivity', 'ProjectTrend'].includes(route.name)" />
    <div class="tab-content-area"><router-view /></div>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import WorkloadScopeBar from './WorkloadScopeBar.vue'
import WorkbenchIcon from './WorkbenchIcon.vue'
const route = useRoute()
const isReview = computed(() => route.path.includes('/code-review'))
const heading = computed(() => ({
  DailyActivity: { title: '成员工作量', description: '结合提交、代码变更与工作摘要，了解团队在所选周期内的实际产出。' },
  ProjectTrend: { title: '项目活跃度', description: '观察项目投入与提交趋势，定位近期变化。' },
  AbsenceActivity: { title: '缺勤跟进', description: '查看无提交成员，结合请假与实际工作情况跟进。' },
  ReportArchive: { title: '日报归档', description: '回顾已归档的团队产出与历史工作记录。' },
}[route.name] || { title: '研发评估', description: '' }))
</script>
