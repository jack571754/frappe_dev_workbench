<template>
  <div class="review-backdrop" @click.self="$emit('close')" @keydown.esc="$emit('close')">
    <section class="review-dialog" role="dialog" aria-modal="true" aria-labelledby="review-create-title">
      <header><div><h2 id="review-create-title">选择要审查的提交</h2><p>OpenCodeReview 初审后，由你复核并线下反馈。</p></div><button class="btn-secondary" @click="$emit('close')" :disabled="busy" aria-label="关闭">关闭</button></header>
      <p v-if="error" role="alert" class="review-error">{{ error }}</p>
      <div v-if="unavailable.length" class="repository-warning" role="status"><strong>{{ unavailable.length }} 个仓库尚未就绪，相关提交暂不可选</strong><p v-for="item in unavailable" :key="item.repository">{{ item.repository }}：{{ item.readiness?.message || '请先检查本机仓库配置' }}</p><button class="btn-secondary" @click="showSetup = true">设置仓库路径</button> <button class="btn-secondary" @click="load" :disabled="loading">重新检查</button></div>
      <p v-if="loading">正在读取成员提交…</p>
      <p v-else-if="!items.length">当前范围没有可审查的提交。</p>
      <div v-else class="review-choices">
        <label v-for="(item, index) in items" :key="`${item.repository}:${item.sha}`">
          <input type="checkbox" :value="index" v-model="selected" :disabled="busy || item.readiness?.status !== 'ready'" />
          <span><strong>{{ item.title || '无提交说明' }}</strong><small>{{ item.repository }} · {{ item.sha?.slice(0, 8) }} · 提交于 {{ (item.committed_at || item.date || '').slice(0, 16) }}</small><small v-if="item.readiness?.status !== 'ready'" class="unavailable">{{ item.readiness?.message || '仓库待检查' }}</small></span>
        </label>
      </div>
      <footer><span>每批最多 20 个提交，分别审查。复用本机第三方模型服务，结果仅保存在工作台。</span><button class="btn-primary" @click="create" :disabled="busy || loading || !selected.length || selected.length > 20">{{ busy ? '正在创建…' : `开始 AI 审查 (${selected.length})` }}</button></footer>
    </section>
    <ReviewRepositorySetup v-if="showSetup" :repository="unavailable[0]?.repository" @close="showSetup = false; load()" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import ReviewRepositorySetup from '@/components/ReviewRepositorySetup.vue'
import { useRouter } from 'vue-router'
import { reviewApi } from '@/utils/codeReview'
const props = defineProps({ member: String, startDate: String, endDate: String, scope: String, repositories: { type: Array, default: () => [] }, shas: { type: Array, default: () => [] } })
defineEmits(['close'])
const router = useRouter()
const items = ref([]), selected = ref([]), loading = ref(true), busy = ref(false), error = ref('')
const showSetup = ref(false)
const unavailable = computed(() => [...new Map(items.value.filter(i => i.readiness?.status !== 'ready').map(i => [i.repository, i])).values()])
async function load() {
  loading.value = true; selected.value = []; error.value = ''
  try {
    const result = await reviewApi('candidates', { member: props.member, start_date: props.startDate, end_date: props.endDate || props.startDate, scope: props.scope || 'all' })
    items.value = result.filter(item => (!props.repositories.length || props.repositories.includes(item.repository)) && (!props.shas.length || props.shas.includes(item.sha)))
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
onMounted(load)
async function create() {
  busy.value = true; error.value = ''
  try {
    const names = await reviewApi('create_tasks', { selections: selected.value.map(i => items.value[i]) }, true)
    await router.push(names.length === 1 ? `/dashboard/code-review/${names[0]}` : '/dashboard/code-review')
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>

<style scoped>
.repository-warning{padding:14px;background:#fff8e9;border:1px solid #f1dfb5;border-radius:7px;margin:14px 0;font-size:12px}.repository-warning p{color:#97621c!important;overflow-wrap:anywhere}.review-choices .unavailable{color:#a45b08}.review-choices label:has(input:disabled){background:#fafafa;cursor:not-allowed}
.review-backdrop{position:fixed;inset:0;background:#0f172a70;z-index:1000;display:flex;align-items:center;justify-content:center;padding:24px}.review-dialog{background:var(--bg-card,#fff);border-radius:12px;box-shadow:var(--shadow-lg);max-width:800px;width:100%;padding:24px}.review-dialog header,.review-dialog footer{display:flex;justify-content:space-between;gap:20px;align-items:center}.review-dialog h2{font-size:20px}.review-dialog p,.review-dialog footer span{color:var(--text-muted);font-size:13px;margin:8px 0}.review-choices{max-height:50vh;overflow:auto;margin:20px 0;border:1px solid var(--border-subtle);border-radius:8px}.review-choices label{display:flex;gap:12px;padding:14px;border-bottom:1px solid var(--border-subtle);cursor:pointer}.review-choices small{display:block;color:var(--text-muted);margin-top:4px}.review-error{color:#b91c1c!important;background:#fef2f2;padding:12px}.review-dialog button:disabled{opacity:.5;cursor:wait}input:focus-visible,button:focus-visible{outline:2px solid var(--primary);outline-offset:3px}@media(max-width:600px){.review-dialog footer{align-items:stretch;flex-direction:column}.review-dialog{padding:16px}}
</style>
