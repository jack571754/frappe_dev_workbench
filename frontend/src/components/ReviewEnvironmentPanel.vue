<template>
  <dialog ref="dialog" class="environment-overlay" aria-labelledby="environment-title" @keydown.esc.stop @cancel.prevent="emit('close')" @click.self="emit('close')">
    <section class="environment-dialog">
      <header><div><h2 id="environment-title">环境与同步</h2><p>检查本机执行端环境，设置数据目录，查看仓库同步路径。</p></div><button class="btn-secondary" @click="emit('close')">关闭</button></header>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
      <p v-else-if="notice" role="status" class="notice">{{ notice }}</p>
      <div class="environment-toolbar">
        <span class="executor-state" :class="online ? 'online' : 'offline'"><i />{{ online ? '执行端在线' : '执行端离线' }}<template v-if="executorLabel">：{{ executorLabel }}</template></span>
        <span class="toolbar-meta">{{ lastSeenText }}<template v-if="toolVersion"> · 工具版本 {{ toolVersion }}</template></span>
      </div>
      <div class="environment-actions">
        <button class="btn-primary" :disabled="!online || !!requesting" @click="requestEnvironment('check')">{{ requesting === 'check' ? '正在请求…' : '一键检查' }}</button>
        <button class="btn-secondary" :disabled="!online || !!requesting" @click="requestEnvironment('setup')">{{ requesting === 'setup' ? '正在请求…' : '一键配置' }}</button>
        <span v-if="!online" class="warning">执行端离线，请先在本机运行 <code>.\start-review-runner.ps1</code> 后再检查或配置。</span>
        <span v-else-if="requestText" class="hint">{{ requestText }}</span>
      </div>
      <section class="environment-checks">
        <div class="section-heading"><h3>环境检查</h3><span v-if="checks.length">{{ passedCount }} / {{ checks.length }} 项通过</span></div>
        <p v-if="!environment" class="empty">执行端尚未上报环境信息。启动执行端后会自动上报，也可以点击「一键检查」请求检查。</p>
        <template v-else>
          <p class="meta">{{ environmentText }}</p>
          <ul v-if="checks.length" class="check-list">
            <li v-for="(item, index) in checks" :key="item.check || item.label || index" :class="item.passed ? 'passed' : 'failed'">
              <strong>{{ item.label || item.check || '未命名检查' }}</strong>
              <span class="check-state">{{ item.passed ? '通过' : '未通过' }}</span>
              <small v-if="item.detail">{{ item.detail }}</small>
            </li>
          </ul>
          <p v-else class="empty">执行端未返回检查项，可点击「一键检查」重新上报。</p>
        </template>
      </section>
      <section class="environment-data-root">
        <div class="section-heading"><h3>数据目录</h3><span>{{ dataRootText }}</span></div>
        <div class="data-root-editor">
          <input v-model="dataRootDraft" type="text" aria-label="执行端数据目录" placeholder="%LOCALAPPDATA%\DevWorkbench" @input="dirty = true" />
          <button class="btn-primary" :disabled="saving || !dataRootDraft.trim()" @click="saveDataRoot">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
        <p class="hint">默认 %LOCALAPPDATA%\DevWorkbench；配置与缓存都在这里，项目目录里不再保存下载内容。</p>
        <p v-if="legacyDataRoot" class="warning">检测到旧目录 {{ legacyDataRoot }}，迁移完成并确认后可以删除。</p>
      </section>
      <section class="environment-repositories">
        <div class="section-heading"><h3>仓库同步路径</h3><span>{{ repositories.length }} 个仓库</span></div>
        <div v-if="repositories.length" class="repository-table-wrap">
          <table class="repository-table">
            <thead><tr><th>仓库</th><th>Codeup 仓库</th><th>本机路径</th><th>就绪状态</th></tr></thead>
            <tbody>
              <tr v-for="repo in repositories" :key="repo.name">
                <td>{{ repo.name || '—' }}</td>
                <td>{{ repo.repository_name || '—' }}</td>
                <td class="path">{{ repo.path || '未登记，执行端检查或配置后自动填写' }}</td>
                <td><span class="readiness" :class="readinessClass(repo)">{{ readinessLabel(repo) }}</span><small v-if="repo.auto_sync" class="auto-sync">自动同步</small></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="empty">暂无仓库同步路径；执行端上报后会自动显示。</p>
      </section>
    </section>
  </dialog>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { reviewApi, repositoryStateLabels, formatReportTime } from '@/utils/codeReview'
const emit = defineEmits(['close'])
const dialog = ref(null), payload = ref(null), loading = ref(false), error = ref(''), notice = ref('')
const requesting = ref(''), saving = ref(false), dirty = ref(false), dataRootDraft = ref('')
let timer, alive = true
const executor = computed(() => payload.value?.executor || {})
const environment = computed(() => payload.value?.environment || null)
const online = computed(() => executor.value.online === true)
const executorLabel = computed(() => executor.value.label || executor.value.name || '')
const toolVersion = computed(() => executor.value.tool_version || '')
const lastSeenText = computed(() => executor.value.last_seen ? `最后上报：${formatReportTime(executor.value.last_seen)}` : '最后上报：尚未上报')
const checks = computed(() => (Array.isArray(environment.value?.checks) ? environment.value.checks : []))
const passedCount = computed(() => checks.value.filter(item => item?.passed).length)
const dataRoot = computed(() => payload.value?.data_root || {})
const reportedDataRoot = computed(() => dataRoot.value.reported || environment.value?.data_root || '')
const configuredDataRoot = computed(() => dataRoot.value.configured || '')
const legacyDataRoot = computed(() => environment.value?.legacy_data_root || '')
const resolvedDataRoot = computed(() => configuredDataRoot.value || reportedDataRoot.value || '')
const repositories = computed(() => (Array.isArray(payload.value?.repositories) ? payload.value.repositories : []))
const request = computed(() => payload.value?.request || {})
const environmentText = computed(() => {
  const parts = []
  if (environment.value?.reported_at) parts.push(`最后上报：${formatReportTime(environment.value.reported_at)}`)
  if (environment.value?.platform) parts.push(`平台：${environment.value.platform}`)
  if (reportedDataRoot.value) parts.push(`上报数据目录：${reportedDataRoot.value}`)
  return parts.length ? parts.join(' · ') : '执行端已上报环境信息'
})
const dataRootText = computed(() => {
  if (configuredDataRoot.value && reportedDataRoot.value && configuredDataRoot.value !== reportedDataRoot.value) return `服务端配置：${configuredDataRoot.value}（执行端待生效）`
  if (configuredDataRoot.value) return `服务端配置：${configuredDataRoot.value}`
  if (reportedDataRoot.value) return `执行端上报：${reportedDataRoot.value}`
  return '尚未配置，使用执行端默认目录'
})
const requestText = computed(() => {
  const mode = request.value.mode
  if (mode !== 'check' && mode !== 'setup') return ''
  const label = mode === 'setup' ? '一键配置' : '一键检查'
  const at = request.value.requested_at ? ` · ${formatReportTime(request.value.requested_at)}` : ''
  return `最近请求：${label}${at}`
})
function readinessState(repo) {
  const value = repo?.readiness
  return typeof value === 'string' ? value : value?.status || ''
}
function readinessLabel(repo) {
  const state = readinessState(repo)
  return repositoryStateLabels[state] || state || '待检查'
}
function readinessClass(repo) {
  return readinessState(repo) === 'ready' ? 'ready' : 'warning'
}
async function load() {
  if (loading.value) return
  loading.value = true
  try {
    const result = await reviewApi('environment_status')
    if (!alive) return
    payload.value = result || null
    if (!dirty.value) dataRootDraft.value = resolvedDataRoot.value
    error.value = ''
  } catch (e) { if (alive) error.value = e.message || '读取环境状态失败' } finally { if (alive) loading.value = false }
}
async function requestEnvironment(mode) {
  if (!online.value || requesting.value) return
  requesting.value = mode
  error.value = ''
  notice.value = ''
  try {
    await reviewApi('request_environment', { mode }, true)
    if (!alive) return
    notice.value = mode === 'check' ? '已请求执行端检查环境，等待上报…' : '已请求执行端配置环境，请留意本机终端输出。'
    await load()
  } catch (e) { if (alive) error.value = e.message || '请求执行端失败' } finally { if (alive) requesting.value = '' }
}
async function saveDataRoot() {
  const value = dataRootDraft.value.trim()
  if (!value || saving.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await reviewApi('save_environment_settings', { data_root: value }, true)
    if (!alive) return
    dirty.value = false
    notice.value = '数据目录已保存，执行端下次上报后生效。'
    await load()
  } catch (e) { if (alive) error.value = e.message || '保存数据目录失败' } finally { if (alive) saving.value = false }
}
onMounted(() => { dialog.value.showModal(); load(); timer = setInterval(load, 5000) })
onUnmounted(() => { alive = false; clearInterval(timer) })
</script>
<style scoped>
.environment-overlay{position:fixed;inset:0;border:0;margin:0;width:100vw;height:100dvh;max-width:100vw;max-height:100dvh;background:transparent;padding:20px;color:var(--text-primary)}.environment-overlay[open]{display:flex;align-items:center;justify-content:center}.environment-overlay::backdrop{background:#17223877}.environment-dialog{width:820px;max-width:100%;max-height:90dvh;overflow:auto;background:#fff;padding:26px;border-radius:12px;box-shadow:0 20px 60px #0f172a33}.environment-dialog header{display:flex;justify-content:space-between;align-items:center;gap:14px}.environment-dialog h2{font-size:21px;font-weight:650}.environment-dialog p{font-size:12px;line-height:1.8;margin:9px 0;color:var(--text-secondary)}.environment-dialog .hint{color:var(--text-muted)}.environment-dialog .meta{color:var(--text-muted)}.environment-dialog .ready{color:#13795b}.environment-dialog .warning{color:#a45b08}.environment-dialog .error{color:#b91c1c}.environment-dialog .notice{color:#13795b}.environment-toolbar{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-top:20px;padding:11px 14px;background:#f8f9fc;border:1px solid var(--border-subtle);border-radius:7px;font-size:12px}.executor-state{display:flex;align-items:center;gap:7px;font-weight:600}.executor-state i{width:7px;height:7px;border-radius:50%;background:#b91c1c;flex-shrink:0}.executor-state.online{color:#13795b}.executor-state.online i{background:#13795b}.executor-state.offline{color:#a45b08}.toolbar-meta{font-size:11px;color:var(--text-muted)}.environment-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:15px 0}.environment-actions button:disabled{opacity:.6;cursor:not-allowed}.environment-checks,.environment-data-root,.environment-repositories{margin-top:18px;padding:14px 15px;border:1px solid var(--border-subtle);border-radius:7px;background:#fff}.section-heading{display:flex;justify-content:space-between;align-items:baseline;gap:12px}.section-heading h3{font-size:13px;font-weight:650}.section-heading span{font-size:11px;color:var(--text-muted);overflow-wrap:anywhere}.empty{margin:10px 0 0;padding:14px;border:1px dashed var(--border-subtle);border-radius:6px;text-align:center;color:var(--text-muted)}.check-list{list-style:none;display:flex;flex-direction:column;gap:8px;margin-top:10px}.check-list li{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:9px 11px;border-radius:6px;background:#f8f9fc;font-size:12px}.check-list li.failed{background:#fff6f6}.check-list strong{font-weight:550;min-width:120px}.check-list .check-state{font-size:11px;padding:2px 7px;border-radius:4px;background:#e8f6ef;color:#13795b;white-space:nowrap}.check-list li.failed .check-state{background:#fdeaea;color:#b91c1c}.check-list small{flex-basis:100%;color:var(--text-muted);font-size:11px;line-height:1.7}.data-root-editor{display:flex;gap:9px;margin-top:10px}.data-root-editor input{flex:1;min-width:0;padding:8px 10px;border:1px solid var(--border-subtle);border-radius:6px;font-size:12px;color:var(--text-primary)}.data-root-editor input:focus{outline:2px solid var(--primary);outline-offset:-1px}.data-root-editor button{flex-shrink:0}.repository-table-wrap{margin-top:10px;border:1px solid var(--border-subtle);border-radius:6px;overflow:auto;max-height:240px}.repository-table{width:100%;border-collapse:collapse;font-size:11px}.repository-table th{text-align:left;padding:9px 11px;background:#f8f9fc;color:var(--text-muted);font-weight:500;white-space:nowrap}.repository-table td{padding:9px 11px;border-top:1px solid #edf0f5;overflow-wrap:anywhere;vertical-align:top}.repository-table .path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;color:var(--text-secondary)}.readiness{display:inline-block;padding:2px 7px;border-radius:4px;font-size:10px;white-space:nowrap;background:#fff6df;color:#a45b08}.readiness.ready{background:#e8f6ef;color:#13795b}.auto-sync{display:block;margin-top:4px;font-size:10px;color:#13795b}code{background:#f8f9fc;padding:1px 5px;border-radius:3px;font-size:11px;user-select:all}button:focus-visible{outline:2px solid var(--primary);outline-offset:-2px}@media(max-width:700px){.environment-dialog{padding:18px}.environment-toolbar{align-items:flex-start;flex-direction:column;gap:6px}.environment-actions{align-items:flex-start;flex-direction:column}.section-heading{flex-wrap:wrap}.data-root-editor{flex-wrap:wrap}.data-root-editor input{flex-basis:100%}.repository-table-wrap{overflow-x:auto}}
</style>
