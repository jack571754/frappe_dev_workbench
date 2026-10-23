<template>
  <div class="workload-scope"><span class="scope-caption"><WorkbenchIcon name="branch" :size="16" />统计分支范围</span><div class="scope-toggle" role="group" aria-label="统计分支范围"><button class="scope-btn" :class="{ active: scope === 'all' }" :aria-pressed="scope === 'all'" @click="setScope('all')">全部分支</button><button class="scope-btn" :class="{ active: scope === 'default' }" :aria-pressed="scope === 'default'" @click="setScope('default')">仅默认分支</button></div><span class="scope-explainer">切换范围后自动更新统计</span></div>
</template>
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import WorkbenchIcon from './WorkbenchIcon.vue'
const scope = ref(localStorage.getItem('dev_workbench_branch_scope') || 'all')
function setScope(value) { scope.value = value; localStorage.setItem('dev_workbench_branch_scope', value); window.dispatchEvent(new CustomEvent('dev_workbench_scope_changed', { detail: { scope: value } })) }
function onScope(e) { scope.value = e.detail?.scope || 'all' }
onMounted(() => window.addEventListener('dev_workbench_scope_changed', onScope))
onUnmounted(() => window.removeEventListener('dev_workbench_scope_changed', onScope))
</script>
