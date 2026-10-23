<template>
  <dialog ref="dialog" class="scan-overlay" aria-labelledby="scan-title" @click.self="close" @cancel.prevent="close">
    <form class="scan-dialog" @submit.prevent="create">
      <h2 id="scan-title">全项目扫描</h2>
      <p>扫描所选分支固定版本的完整文件，仅生成私有报告供人工复核。</p>
      <label>仓库<select v-model="repository" @change="loadBranches" :disabled="busy"><option value="">请选择仓库</option><option v-for="r in repos" :key="r.name" :value="r.name">{{ r.repository_name || r.name }}{{ r.scan_readiness?.status === 'ready' ? ' · 已就绪' : ' · 需配置' }}</option></select></label>
      <div v-if="repository && !ready" class="repository-warning" role="status"><p>{{ current?.scan_readiness?.message || '请先检查本机仓库配置' }}</p><button type="button" class="btn-secondary" @click="showSetup = true">设置仓库路径</button> <button type="button" class="btn-secondary" @click="checkRepository" :disabled="checking">{{ checking ? '检查中…' : '重新检查' }}</button></div>
      <label>分支<select v-model="branch" :disabled="busy || branchesLoading || !repository || !ready"><option value="">{{ branchesLoading ? '正在读取分支…' : '请选择分支' }}</option><option v-for="b in branches" :key="b" :value="b">{{ b }}</option></select></label>
      <p class="scan-note">不限制 token 总预算。敏感文件、二进制、隐藏配置和生成目录会跳过；单文件 500KB、总材料 20MB，未覆盖内容会在报告中列明。不会修改或提交代码。</p>
      <p v-if="error" role="alert" class="scan-error">{{ error }}</p>
      <footer><button type="button" class="btn-secondary" @click="close" :disabled="busy">取消</button><button type="submit" class="btn-primary" :disabled="busy || checking || branchesLoading || !branch || !ready">{{ busy ? '创建中…' : '开始全扫' }}</button></footer>
    </form>
    <ReviewRepositorySetup v-if="showSetup" :repository="repository" @close="showSetup = false; checkRepository()" />
  </dialog>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import ReviewRepositorySetup from '@/components/ReviewRepositorySetup.vue'
import { reviewApi } from '@/utils/codeReview'
const emit = defineEmits(['close', 'created'])
const dialog = ref(null)
function close() { if (!busy.value) emit('close') }
const repos = ref([]), repository = ref(''), branch = ref(''), branches = ref([]), branchesLoading = ref(false), busy = ref(false), error = ref('')
const showSetup = ref(false), checking = ref(false)
const current = computed(() => repos.value.find(r => r.name === repository.value))
const ready = computed(() => current.value?.scan_readiness?.status === 'ready')
async function checkRepository() {
  checking.value = true; error.value = ''
  try { repos.value = await reviewApi('scan_options'); await loadBranches() }
  catch (e) { error.value = e.message } finally { checking.value = false }
}
let generation = 0
async function loadBranches() {
  const current = ++generation, selected = repository.value
  branch.value = ''; branches.value = []; error.value = ''
  if (!selected || !ready.value) { branchesLoading.value = false; return }
  branchesLoading.value = true
  try {
    const result = await reviewApi('scan_options', { repository: selected })
    if (current !== generation) return
    branches.value = result
    const preferred = repos.value.find(r => r.name === selected)?.default_branch
    branch.value = result.includes(preferred) ? preferred : result[0] || ''
  } catch (e) { if (current === generation) error.value = e.message }
  finally { if (current === generation) branchesLoading.value = false }
}
async function create() {
  if (busy.value || !repository.value || !branch.value || !ready.value) return
  busy.value = true; error.value = ''
  try { const name = await reviewApi('create_scan_task', { repository: repository.value, branch: branch.value }, true); emit('created', name) }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
onMounted(async () => { dialog.value.showModal(); try { repos.value = await reviewApi('scan_options') } catch (e) { error.value = e.message } })
</script>
<style scoped>
.repository-warning{padding:12px;background:#fff8e9;border:1px solid #f1dfb5;border-radius:6px;margin:12px 0}.repository-warning p{color:#97621c;overflow-wrap:anywhere}
.scan-overlay{position:fixed;inset:0;border:0;margin:0;width:100vw;height:100dvh;max-width:100vw;max-height:100dvh;background:transparent;padding:20px;color:var(--text-primary)}.scan-overlay[open]{display:flex;align-items:center;justify-content:center}.scan-overlay::backdrop{background:#17223877}.scan-dialog{width:540px;max-width:100%;background:white;padding:26px;border-radius:12px;box-shadow:0 20px 60px #0f172a33}.scan-dialog h2{font-size:21px;font-weight:650}.scan-dialog p{font-size:13px;color:var(--text-muted);margin:12px 0;line-height:1.7}.scan-dialog label{display:block;font-size:13px;margin-top:18px}.scan-dialog select{display:block;width:100%;margin-top:7px;padding:9px;border:1px solid var(--border-subtle);border-radius:6px;background:white}.scan-dialog footer{display:flex;justify-content:flex-end;gap:10px;margin-top:22px}.scan-dialog .scan-error{color:#b91c1c}.scan-dialog button:disabled{opacity:.5}select:focus-visible,button:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
</style>
