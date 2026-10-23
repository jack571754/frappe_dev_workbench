<template>
  <dialog ref="dialog" class="repository-overlay" aria-labelledby="repository-setup-title" @keydown.esc.stop @cancel.prevent="$emit('close')" @click.self="$emit('close')">
    <section class="repository-dialog">
      <header><div><h2 id="repository-setup-title">本机仓库设置</h2><p>一键下载审查代码，自动配置路径与版本同步。</p></div><button class="btn-secondary" @click="$emit('close')">关闭</button></header>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
      <div class="repository-toolbar"><span>{{ readyCount }} / {{ repos.length }} 个仓库可审查</span><button class="btn-secondary" @click="load" :disabled="loading">{{ loading ? '检查中…' : '重新检查' }}</button></div>
      <p class="hint">复用工作台现有 Codeup 凭证，下载到本机专用审查缓存，不改动开发目录。此窗口会自动刷新准备进度。</p>
      <div class="repository-list"><button v-for="r in repos" :key="r.name" :class="{ selected: selected === r.name }" @click="selected = r.name"><span>{{ r.repository_name || r.name }}</span><strong :class="r.readiness.status === 'ready' && !pending(r) ? 'ready' : 'warning'">{{ pending(r) ? preparationLabels[r.preparation.status] : r.readiness.auto_sync ? '自动同步' : labels[r.readiness.status] || '待检查' }}</strong></button></div>
      <section v-if="current" class="repository-instructions">
        <h3>{{ current.repository_name || current.name }}</h3><p :class="current.readiness.status === 'ready' ? 'ready' : 'warning'">{{ current.readiness.message }}</p>
        <p v-if="current.readiness.auto_sync" class="ready">已启用自动同步：每次审查前自动下载所需提交及父版本，无需手动拉取代码。</p>
        <p v-else-if="current.readiness.status === 'ready'">已有本机目录可用。启用自动同步后，会改用独立审查缓存，不再需要手动更新这个仓库。</p>
        <p v-else>点击下方按钮即可自动下载、校验并登记路径，无需寻找目录或修改配置文件。</p>
        <div class="prepare-actions"><button class="btn-primary" @click="prepare" :disabled="requesting || !current.can_prepare || pending(current)">{{ requesting ? '正在提交…' : pending(current) ? preparationLabels[current.preparation.status] : current.readiness.auto_sync ? '重新准备仓库' : current.readiness.status === 'ready' ? '启用自动同步' : '一键准备仓库' }}</button><span v-if="current.can_prepare">执行端：{{ current.preparation_executor }}</span></div>
        <p v-if="pending(current)" role="status">{{ current.preparation.status === 'queued' ? '准备任务已排队。当前审查完成后，执行端会自动下载；可以关闭此窗口。' : '正在下载并校验仓库，完成后自动配置。请保持执行端在线，可以关闭此窗口。' }}</p>
        <p v-else-if="current.preparation?.status === 'failed'" class="error" role="alert">{{ current.preparation.error || '仓库准备失败，请重试' }}</p>
        <p v-if="!current.can_prepare" class="warning">请先启动支持一键准备的新版执行端。升级后停止旧进程，再运行 <code>.\start-review-runner.ps1</code>。</p>
        <details class="manual-setup"><summary>使用已有代码目录手动配置</summary>
        <p>在当前电脑准备好这个仓库的本地 Git 目录。进入执行器目录，将下方路径替换为真实路径后，在 PowerShell 运行：</p>
        <pre><code>{{ command }}</code></pre>
        <p>配置工具会验证目录，并保留原有模型及连接配置。每个仓库配置一次，多个提交共用；也支持裸仓库目录。</p>
        </details>
      </section>
    </section>
  </dialog>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { reviewApi } from '@/utils/codeReview'
const props = defineProps({ repository: { type: String, default: '' } })
const emit = defineEmits(['close', 'checked'])
const dialog = ref(null), repos = ref([]), selected = ref(props.repository), loading = ref(false), error = ref('')
const requesting = ref(false), preparationLabels = { queued: '等待下载', preparing: '正在下载…' }
let timer, alive = true
function pending(repo) { return ['queued', 'preparing'].includes(repo.preparation?.status) }
const labels = { ready: '已就绪', unavailable: '路径不可用', not_configured: '未配置', offline: '执行端未就绪' }
const readyCount = computed(() => repos.value.filter(r => r.readiness.status === 'ready').length)
const current = computed(() => repos.value.find(r => r.name === selected.value))
const command = computed(() => `.\\configure-repository.ps1 -Repository '${(selected.value || '').replaceAll("'", "''")}' -Path 'D:\\你的代码目录\\仓库目录'`)
async function load() {
  if (loading.value) return
  loading.value = true; error.value = ''
  try { const result = await reviewApi('repository_readiness'); if (!alive) return; repos.value = result; if (!selected.value) selected.value = repos.value.find(r => r.readiness.status !== 'ready')?.name || repos.value[0]?.name || ''; emit('checked') }
  catch (e) { if (alive) error.value = e.message } finally { if (alive) loading.value = false }
}
async function prepare() {
  if (!current.value || requesting.value || pending(current.value) || !current.value.can_prepare) return
  requesting.value = true; error.value = ''
  try { await reviewApi('prepare_repository', { repository: selected.value }, true); if (alive) await load() }
  catch (e) { if (alive) error.value = e.message } finally { if (alive) requesting.value = false }
}
onMounted(() => { dialog.value.showModal(); load(); timer = setInterval(load, 5000) })
onUnmounted(() => { alive = false; clearInterval(timer) })
</script>
<style scoped>
.prepare-actions{display:flex;align-items:center;gap:12px;margin:15px 0;flex-wrap:wrap}.prepare-actions span{font-size:11px;color:var(--text-muted)}.prepare-actions button:disabled{opacity:.6;cursor:not-allowed}.manual-setup{margin-top:18px;font-size:12px;color:var(--text-secondary)}.manual-setup summary{cursor:pointer}
.repository-overlay{position:fixed;inset:0;border:0;margin:0;width:100vw;height:100dvh;max-width:100vw;max-height:100dvh;background:transparent;padding:20px;color:var(--text-primary)}.repository-overlay[open]{display:flex;align-items:center;justify-content:center}.repository-overlay::backdrop{background:#17223877}.repository-dialog{width:760px;max-width:100%;max-height:90dvh;overflow:auto;background:#fff;padding:26px;border-radius:12px;box-shadow:0 20px 60px #0f172a33}.repository-dialog header,.repository-toolbar{display:flex;justify-content:space-between;align-items:center;gap:14px}.repository-dialog h2{font-size:21px;font-weight:650}.repository-dialog p{font-size:12px;line-height:1.8;margin:9px 0;color:var(--text-secondary)}.repository-toolbar{margin-top:20px;font-size:13px}.repository-list{margin:16px 0;border:1px solid var(--border-subtle);border-radius:7px;max-height:230px;overflow:auto}.repository-list button{width:100%;padding:12px 14px;display:flex;align-items:center;justify-content:space-between;gap:16px;text-align:left;border-bottom:1px solid #edf0f5;font-size:12px}.repository-list button:last-child{border-bottom:0}.repository-list button.selected{background:#f1efff}.repository-list button span{overflow-wrap:anywhere;min-width:0}.repository-list strong{white-space:nowrap;font-size:11px;font-weight:500}.repository-instructions{padding:15px;background:#f8f9fc;border:1px solid var(--border-subtle);border-radius:7px}.repository-instructions h3{font-size:13px;font-weight:650;overflow-wrap:anywhere}.repository-instructions pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;padding:12px;border:1px solid var(--border-subtle);font-size:12px;border-radius:5px;user-select:all}.repository-dialog .ready{color:#13795b}.repository-dialog .warning{color:#a45b08}.repository-dialog .error{color:#b91c1c}.repository-dialog .hint{color:var(--text-muted)}button:focus-visible{outline:2px solid var(--primary);outline-offset:-2px}@media(max-width:650px){.repository-dialog{padding:18px}.repository-overlay{padding:12px}}
</style>
