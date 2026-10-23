<template>
  <main class="review-detail">
    <router-link to="/dashboard/code-review" class="back-link">← 返回代码审查</router-link>
    <header v-if="task" class="detail-heading"><div><h1>{{ task.title || '提交审查' }}</h1><p>{{ task.review_mode === 'scan' ? '全项目 · ' + task.branch : task.member_name }} · {{ task.repository }} · <code>{{ task.head_sha }}</code><template v-if="task.committed_at"> · 提交于 {{ task.committed_at.slice(0, 16) }}</template></p></div><span :class="['status-label', task.status]">{{ states[task.status] }}</span></header>
    <p v-if="error" role="alert" class="notice error">{{ error }}</p><p v-if="message" role="status" class="notice">{{ message }}</p>
    <p v-if="loading && !task">正在读取审查任务…</p>
    <template v-if="task">
      <div class="detail-toolbar">
        <span class="review-progress-label">人工复核：{{ reviewStates[task.review_status] }}<template v-if="task.attempt?.tool_version"> · 引擎：{{ task.attempt.tool_version }}</template></span>
        <select v-if="task.attempts?.length" v-model="attemptName" @change="load" aria-label="报告版本" title="选择历史报告"><option v-for="a in task.attempts" :key="a.name" :value="a.name">{{ a.started_at || a.creation }} · {{ states[a.status] || a.status }}</option></select>
        <button class="btn-secondary" @click="load" :disabled="busy">刷新</button>
        <button v-if="activeStates.includes(task.status)" class="btn-secondary" @click="action('cancel_task')" :disabled="busy">取消任务</button>
        <button v-else class="btn-secondary" @click="action('retry_task')" :disabled="busy || task.readiness?.status !== 'ready'" :title="task.readiness?.message">重新审查</button>
        <button class="btn-secondary" @click="copyFeedback" :disabled="!confirmed.length">复制已确认问题 ({{ confirmed.length }})</button>
        <button v-if="['completed','partial'].includes(task.status) && !historical" class="btn-primary" @click="action('complete_review')" :disabled="busy || pendingCount > 0 || task.review_status === 'completed'">完成复核</button>
      </div>
      <p v-if="historical" class="notice">正在查看历史报告，仅供阅读。</p>
      <div v-if="task.readiness?.status !== 'ready'" class="notice repository-warning" role="status"><div><strong>审查前需要完成仓库检查</strong><p>{{ task.readiness?.message || '请检查本机仓库配置' }} · {{ task.repository }}</p></div><button class="btn-secondary" @click="showSetup = true">设置仓库路径</button><button class="btn-secondary" @click="load" :disabled="loading">重新检查</button></div>
      <p v-if="task.status === 'queued'" class="notice">任务已排队。执行端通过认证和只读预检后领取任务；电脑离线时继续保留。</p>
      <p v-if="task.attempt?.error" class="notice error">{{ task.attempt.error }}</p>
      <div v-if="report.summary" class="report-summary"><strong>AI 审查摘要</strong><p>{{ report.summary }}</p><p v-if="report.partial" class="coverage-warning">本次为部分审查，请结合未覆盖内容判断。</p><ul v-if="report.limitations?.length"><li v-for="(item, i) in report.limitations" :key="i">{{ item }}</li></ul></div>
      <div v-if="materials.changes?.length || findings.length" class="workspace-controls"><span>{{ task.review_mode === 'scan' ? '扫描文件' : '变更文件' }} {{ materials.changes?.length || 0 }}<span class="workspace-count-separator">/</span>{{ findings.length }} 项候选问题</span><div class="workspace-display-tools"><label v-if="!focusCode" class="panel-size-control">问题面板<input type="range" v-model.number="findingsWidth" min="280" max="480" step="20" aria-label="问题面板宽度" /></label><button class="btn-secondary" :aria-pressed="focusCode" @click="focusCode = !focusCode">{{ focusCode ? '恢复三栏' : '专注代码' }}</button></div></div>
      <div v-if="materials.changes?.length || findings.length" :class="['review-workspace', { 'code-focus': focusCode }]" :style="{ '--findings-width': findingsWidth + 'px' }">
        <nav class="file-panel" aria-label="变更文件"><h2>{{ task.review_mode === 'scan' ? '扫描文件' : '变更文件' }} <span>{{ materials.changes?.length || 0 }}</span></h2><button v-for="file in materials.changes || []" :key="file.path" :class="['file-button', { selected: selectedPath === file.path }]" @click="selectedPath = file.path"><span>{{ file.path }}</span><small>{{ file.skipped ? '未覆盖' : `${fileCounts[file.path] || 0} 项问题` }}</small></button></nav>
        <section class="code-panel" aria-label="代码差异"><header><code>{{ selectedFile?.path || '选择文件' }}</code><select v-model="codeMode" aria-label="代码显示方式"><option v-if="task.review_mode !== 'scan'" value="diff">代码差异</option><option value="new">新版本全文</option><option v-if="task.review_mode !== 'scan'" value="old">旧版本全文</option></select></header><p v-if="selectedFile?.skipped" class="notice">{{ selectedFile.skipped }}</p><div v-else class="code-scroll"><table class="code-table"><tbody><tr v-for="(line, index) in codeLines" :key="index" :id="`code-line-${index}`" :class="[line.kind, { focused: isFocused(line) }]"><td class="line-number">{{ line.old || '' }}</td><td class="line-number">{{ line.new || '' }}</td><td><pre>{{ line.text || ' ' }}</pre></td></tr></tbody></table><p v-if="!codeLines.length" class="code-empty">此版本没有文件内容。</p></div></section>
        <section class="finding-panel" aria-label="审查问题"><h2>审查发现 <span>{{ findings.length }}</span></h2><p v-if="!findings.length" class="no-findings">{{ emptyReviewMessage(task.attempt?.status || task.status, report) }}</p><article v-for="f in findings" :key="f.name" class="finding-card"><div class="finding-top"><span :class="['severity', f.severity]">{{ severityLabels[f.severity] }}</span><span>{{ decisionLabels[f.decision] }}</span></div><button class="finding-title" @click="locate(f)">{{ f.title }}</button><button class="finding-location" @click="locate(f)">{{ f.path }}{{ f.located ? `:${f.line} · ${f.side === 'old' ? '旧' : '新'}版本` : ' · 未定位' }}</button><dl><dt>触发条件</dt><dd>{{ f.trigger || '未说明' }}</dd><dt>影响</dt><dd>{{ f.impact }}</dd><dt>代码依据</dt><dd>{{ f.evidence }}</dd><dt>建议</dt><dd>{{ f.suggestion }}</dd><template v-if="f.uncertainty"><dt>尚待核实</dt><dd>{{ f.uncertainty }}</dd></template></dl><label class="note-label">你的私有备注<textarea v-model="f.note" :disabled="historical || busy" rows="2" maxlength="10000" /></label><label class="feedback-check"><input type="checkbox" v-model="f.feedback" :disabled="historical || busy" />已线下反馈</label><div v-if="!historical" class="finding-actions"><button class="btn-primary" @click="save(f, 'confirmed')" :disabled="busy">确认问题</button><button class="btn-secondary" @click="save(f, 'ignored')" :disabled="busy">忽略</button><button class="btn-secondary" @click="save(f, f.decision)" :disabled="busy">保存备注</button></div></article></section>
      </div>
      <details v-if="report.coverage" class="coverage-details"><summary>覆盖范围：{{ report.coverage.reviewed?.length || 0 }} 个文件有完成凭据，{{ report.coverage.skipped?.length || 0 }} 个文件未确认覆盖</summary><ul v-if="report.coverage.skipped?.length"><li v-for="item in report.coverage.skipped.slice(0, 200)" :key="item.path"><code>{{ item.path }}</code><span>{{ item.reason }}</span></li></ul><p v-if="report.coverage.skipped?.length > 200">其余文件请查看原始报告。</p></details>
      <section v-if="task.attempt?.raw_report || task.attempt?.report" class="report-export-section" aria-label="审查报告导出"><header><div><h2>原始审查报告</h2><p>导出当前选中的报告版本，包含可读结果和完整原始输出。</p></div><button class="btn-secondary" @click="exportMarkdown" :disabled="busy || loading || !exportReady">导出 Markdown</button></header><details v-if="task.attempt?.raw_report" class="raw-report"><summary>展开原始输出</summary><pre>{{ task.attempt.raw_report }}</pre></details></section>
      <section v-if="copyFallback" class="copy-fallback"><label>请手动复制反馈内容<textarea readonly :value="copyFallback" rows="10" /></label><button class="btn-secondary" @click="copyFallback = ''">关闭</button></section>
    </template>
    <ReviewRepositorySetup v-if="showSetup" :repository="task?.repository" @close="showSetup = false; load()" />
  </main>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import ReviewRepositorySetup from '@/components/ReviewRepositorySetup.vue'
import { parseDiff } from '@/utils/codeReviewDiff'
import { buildReviewMarkdown, reviewMarkdownFilename } from '@/utils/reviewMarkdown'
import { emptyReviewMessage } from '@/utils/reviewPresentation'
import { reviewApi, states, reviewStates, severityLabels, decisionLabels, activeStates, parseJson, feedbackText } from '@/utils/codeReview'
const route = useRoute()
const showSetup = ref(false)
const task = ref(null), findings = ref([]), loading = ref(false), busy = ref(false), error = ref(''), message = ref(''), selectedPath = ref(''), attemptName = ref(''), codeMode = ref('diff'), findingsWidth = ref(340), focusCode = ref(false), focused = ref(null), copyFallback = ref('')
let alive = true, timer, generation = 0
const materials = computed(() => parseJson(task.value?.attempt?.materials))
const report = computed(() => parseJson(task.value?.attempt?.report))
const selectedFile = computed(() => materials.value.changes?.find(f => f.path === selectedPath.value))
const confirmed = computed(() => findings.value.filter(f => f.decision === 'confirmed'))
const pendingCount = computed(() => findings.value.filter(f => f.decision === 'pending').length)
const exportReady = computed(() => !!task.value?.attempt && (!attemptName.value || attemptName.value === task.value.attempt.name))
const historical = computed(() => !!attemptName.value && attemptName.value !== task.value?.current_attempt)
const fileCounts = computed(() => findings.value.reduce((counts, f) => { counts[f.path] = (counts[f.path] || 0) + 1; return counts }, {}))
const codeLines = computed(() => {
  const f = selectedFile.value
  if (!f) return []
  if (codeMode.value !== 'diff') {
    const content = f[codeMode.value] || ''
    if (!content) return []
    const lines = content.split('\n'); if (lines.at(-1) === '') lines.pop()
    return lines.map((text, i) => ({ text, [codeMode.value]: i + 1, kind: '' }))
  }
  return parseDiff(f.diff || '')
})
function isFocused(line) { return focused.value && focused.value.path === selectedPath.value && line[focused.value.side] >= focused.value.line && line[focused.value.side] <= focused.value.end_line }
async function locate(f) {
  selectedPath.value = f.path; focused.value = f
  if (!f.located) return
  codeMode.value = f.side
  await nextTick()
  const index = codeLines.value.findIndex(line => line[f.side] === f.line)
  document.getElementById(`code-line-${index}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}
async function load() {
  const current = ++generation, name = route.params.id
  loading.value = true
  try {
    const result = await reviewApi('get_task', { name, ...(attemptName.value ? { attempt_name: attemptName.value } : {}) })
    if (!alive || current !== generation) return
    if (result.review_mode === 'scan' && codeMode.value === 'diff') codeMode.value = 'new'
    task.value = result; attemptName.value = result.attempt?.name || ''
    findings.value = (result.findings || []).map(f => ({ ...f, feedback: !!f.feedback_at }))
    const changes = parseJson(result.attempt?.materials).changes || []
    if (!changes.some(f => f.path === selectedPath.value)) selectedPath.value = changes[0]?.path || ''
    error.value = ''
  } catch (e) { if (alive && current === generation) error.value = e.message }
  finally { if (alive && current === generation) loading.value = false }
}
async function action(method) {
  busy.value = true; message.value = ''
  try { await reviewApi(method, { name: task.value.name }, true); if (method === 'retry_task') attemptName.value = ''; await load() }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
async function save(f, decision) {
  busy.value = true
  try { await reviewApi('update_finding', { name: f.name, decision, note: f.note || '', feedback: f.feedback ? 1 : 0 }, true); f.decision = decision; task.value.review_status = 'in_progress'; message.value = '复核记录已保存'; error.value = '' }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
function exportMarkdown() {
  if (busy.value || loading.value || !exportReady.value) return
  let url
  try {
    const blob = new Blob(['\ufeff', buildReviewMarkdown(task.value)], { type: 'text/markdown;charset=utf-8' })
    url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = reviewMarkdownFilename(task.value)
    document.body.appendChild(link)
    try { link.click() } finally { link.remove() }
    message.value = '已生成 Markdown 文件，请查看浏览器下载。'; error.value = ''
  } catch { error.value = '导出失败，请刷新报告后重试。' }
  finally { if (url) setTimeout(() => URL.revokeObjectURL(url), 1000) }
}
async function copyFeedback() {
  const value = feedbackText(task.value, findings.value)
  if (!value) return
  try { await navigator.clipboard.writeText(value); message.value = '已复制，可用于线下反馈' } catch { copyFallback.value = value }
}
watch(() => route.params.id, () => { attemptName.value = ''; task.value = null; load() })
onMounted(() => { load(); timer = setInterval(() => { if (!busy.value && !loading.value && task.value && activeStates.includes(task.value.status) && !historical.value) load() }, 10000) })
onUnmounted(() => { alive = false; generation++; clearInterval(timer) })
</script>

<style scoped>
.repository-warning{display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:#fff8e9!important;color:#97621c!important}.repository-warning>div{flex:1 1 300px}.repository-warning strong{font-size:13px}.repository-warning p{font-size:12px;margin-top:6px;overflow-wrap:anywhere}.repository-warning button{font-size:12px}
.back-link{font-size:13px;color:var(--text-muted)}.detail-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;margin:16px 0}.detail-heading h1{font-size:23px;font-weight:650}.detail-heading p{font-size:12px;color:var(--text-muted);margin-top:8px;overflow-wrap:anywhere}.status-label{white-space:nowrap;padding:5px 10px;background:#eef2ff;color:#4338ca;border-radius:5px;font-size:13px}.status-label.failed{background:#fef2f2;color:#b91c1c}.detail-toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:14px 0;border-top:1px solid var(--border-subtle);font-size:12px}.detail-toolbar>span{margin-right:auto}.detail-toolbar button{font-size:12px;padding:7px 10px}.detail-toolbar select,.code-panel select{max-width:230px;border:1px solid var(--border-subtle);border-radius:5px;padding:6px;background:white}.notice{padding:12px 16px;background:#eff6ff;color:#1e40af;border-radius:6px;margin:12px 0;font-size:13px}.notice.error{background:#fef2f2;color:#b91c1c}.report-summary{background:white;border:1px solid var(--border-subtle);padding:16px;border-radius:8px;font-size:13px;margin:12px 0 20px}.report-summary>p{margin-top:6px;white-space:pre-wrap}.report-summary ul{margin:8px 0 0 20px;color:var(--text-muted)}.coverage-warning{color:#92400e}.review-workspace{display:grid;grid-template-columns:190px minmax(300px,1fr) 350px;gap:12px;align-items:start}.file-panel,.code-panel,.finding-panel{border:1px solid var(--border-subtle);border-radius:8px;background:white;min-width:0;overflow:hidden}.file-panel h2,.finding-panel h2{font-size:13px;padding:14px;border-bottom:1px solid var(--border-subtle);display:flex;justify-content:space-between}.file-panel h2 span,.finding-panel h2 span{color:var(--text-muted)}.file-button{display:block;padding:12px;width:100%;text-align:left;font-size:12px;border-bottom:1px solid var(--border-subtle);overflow-wrap:anywhere}.file-button.selected{background:var(--primary-light);color:var(--primary);box-shadow:inset 3px 0 var(--primary)}.file-button small{display:block;color:var(--text-muted);margin-top:4px}.code-panel>header{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;border-bottom:1px solid var(--border-subtle);font-size:12px}.code-panel>header code{overflow-wrap:anywhere}.code-scroll{overflow:auto;max-height:75vh;min-height:280px}.code-table{border-collapse:collapse;width:100%;font-size:12px;line-height:1.75}.code-table pre{font-family:Consolas,'SFMono-Regular',monospace;white-space:pre;margin:0;padding:0 10px}.line-number{user-select:none;min-width:34px;text-align:right;color:#94a3b8;border-right:1px solid #e2e8f0;padding:0 7px;font-family:monospace;vertical-align:top}.added{background:#ecfdf5}.removed{background:#fff1f2}.hunk{background:#f1f5f9;color:#64748b}.focused{background:#fef3c7!important;box-shadow:inset 3px 0 #d97706}.finding-panel{max-height:80vh;overflow:auto}.finding-card{padding:16px;border-bottom:1px solid var(--border-subtle)}.finding-top{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--text-muted)}.severity{background:#f1f5f9;padding:3px 7px;border-radius:4px}.severity.high{background:#fee2e2;color:#b91c1c}.severity.medium{background:#fef3c7;color:#92400e}.severity.low{background:#dbeafe;color:#1e40af}.finding-title{font-size:14px;font-weight:650;text-align:left;margin:10px 0 6px}.finding-location{display:block;color:var(--primary);font-family:monospace;font-size:11px;text-align:left;overflow-wrap:anywhere}.finding-card dl{font-size:12px;margin-top:12px}.finding-card dt{color:var(--text-muted);margin-top:10px}.finding-card dd{margin-top:3px;white-space:pre-wrap;overflow-wrap:anywhere}.note-label{font-size:12px;color:var(--text-muted);display:block;margin-top:16px}.note-label textarea,.copy-fallback textarea{display:block;width:100%;border:1px solid var(--border-subtle);border-radius:5px;padding:8px;margin-top:6px;font:inherit;resize:vertical}.feedback-check{display:flex;align-items:center;gap:6px;font-size:12px;margin:10px 0}.finding-actions{display:flex;gap:6px;flex-wrap:wrap}.finding-actions button{font-size:11px;padding:6px 9px}.no-findings,.code-empty{padding:20px;font-size:13px;color:var(--text-muted)}.raw-report{font-size:13px;margin-top:20px;color:var(--text-muted)}.raw-report summary{cursor:pointer}.raw-report pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto;margin-top:10px;padding:16px;background:#f8fafc}.copy-fallback{padding:20px;background:white;border:1px solid var(--border-subtle)}button:disabled{opacity:.45;cursor:not-allowed}button:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--primary);outline-offset:2px}@media(max-width:1150px){.review-workspace{grid-template-columns:150px minmax(250px,1fr)}.finding-panel{grid-column:1/-1;max-height:none}}@media(max-width:650px){.review-workspace{grid-template-columns:1fr}.file-panel,.finding-panel{grid-column:auto}.file-panel{max-height:220px;overflow:auto}.detail-heading{align-items:start}.detail-heading h1{font-size:19px}.detail-toolbar>span{flex-basis:100%}}

.review-detail{min-width:0}.back-link{display:inline-block;font-size:12px;color:var(--text-secondary);padding:0 0 5px}.detail-heading{margin:14px 0 23px;align-items:flex-start}.detail-heading h1{font-size:24px;line-height:1.5;max-width:65ch}.detail-heading p{font-size:12px;margin-top:10px;line-height:1.8}.detail-heading code{font-size:11px}.status-label{margin-top:5px;font-size:12px}.detail-toolbar{gap:9px;padding:16px 0;align-items:center}.review-progress-label{font-size:12px;color:var(--text-secondary);line-height:1.8;flex:1 1 300px}.detail-toolbar select{font-size:11px;max-width:215px;min-width:140px;text-overflow:ellipsis}.report-summary{padding:18px 20px;font-size:13px;line-height:1.8;border-left:3px solid var(--primary)}.report-summary>strong{font-size:13px;font-weight:650}.report-summary ul{color:var(--text-secondary);font-size:12px}.workspace-controls{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:6px 0 13px;font-size:12px;color:var(--text-secondary)}.workspace-count-separator{margin:0 12px;color:#bcc4d2}.workspace-display-tools{display:flex;gap:18px;align-items:center}.panel-size-control{display:flex;gap:10px;align-items:center;font-size:11px;color:var(--text-muted)}.panel-size-control input{width:85px;accent-color:var(--primary)}.workspace-controls .btn-secondary{font-size:11px;min-height:30px;padding:4px 10px}.review-workspace{grid-template-columns:190px minmax(0,1fr) var(--findings-width,340px);gap:14px}.file-panel,.code-panel,.finding-panel{border-radius:7px}.file-panel,.finding-panel{position:sticky;top:82px;max-height:calc(100vh - 110px);overflow-y:auto}.file-panel h2,.finding-panel h2{background:#f8f9fc;font-weight:600;position:sticky;top:0;z-index:2;min-height:48px;font-size:12px}.file-button{font-size:12px;line-height:1.7;padding:13px 12px}.file-button small{font-size:10px}.code-panel>header{min-height:48px;background:#fcfcfe}.code-panel>header code{font-size:11px;line-height:1.6}.code-panel select{font-size:11px;padding:5px;max-width:125px;flex-shrink:0}.code-scroll{max-height:calc(100vh - 165px);min-height:420px}.code-table{font-size:12px;line-height:1.9}.code-table pre{padding:0 12px}.finding-card{padding:18px 16px}.finding-title{overflow-wrap:anywhere;word-break:break-word;max-width:100%;font-size:14px;line-height:1.65;margin:12px 0 8px}.finding-location{font-size:11px;line-height:1.7}.finding-card dl{font-size:12px;line-height:1.8}.finding-card dt{font-size:11px}.finding-actions{position:sticky;bottom:-1px;padding:12px 0 2px;background:#fff;border-top:1px solid var(--border-subtle);margin-top:14px}.finding-actions button{font-size:11px;min-height:30px}.no-findings{line-height:1.8;font-size:12px}.code-focus{grid-template-columns:minmax(0,1fr)}.code-focus .file-panel,.code-focus .finding-panel{display:none}.coverage-details{margin:20px 0;font-size:12px;color:var(--text-secondary)}.coverage-details summary{cursor:pointer;line-height:1.8}.coverage-details ul{margin-top:12px;max-height:230px;overflow:auto;border:1px solid var(--border-subtle);background:#fff;border-radius:6px;padding:10px 15px;list-style:none}.coverage-details li{padding:7px 0;border-bottom:1px solid #edf0f5;display:flex;justify-content:space-between;gap:14px;font-size:11px}.coverage-details code{overflow-wrap:anywhere;min-width:0}.coverage-details li>span{color:var(--text-muted);max-width:55%;text-align:right}.raw-report{font-size:12px}.raw-report pre{background:#fff;border:1px solid var(--border-subtle);border-radius:7px;font-size:11px}
@media(max-width:1300px){.review-workspace{grid-template-columns:165px minmax(0,1fr)}.finding-panel{position:static;max-height:none;grid-column:1/-1}.panel-size-control{display:none}.finding-card{padding:20px}.finding-card dl{display:grid;grid-template-columns:74px minmax(0,1fr);gap:10px}.finding-card dt{margin:0}.finding-card dd{margin:0}.finding-actions{position:static}.code-focus{grid-template-columns:minmax(0,1fr)}}
@media(max-width:650px){.detail-heading h1{font-size:20px}.detail-heading{gap:12px}.detail-heading p{font-size:11px}.detail-heading code{word-break:break-all}.status-label{font-size:10px;padding:5px 6px}.review-workspace{grid-template-columns:minmax(0,1fr)}.file-panel,.finding-panel{position:static;max-height:none;grid-column:auto}.file-panel{max-height:220px}.file-panel h2{font-size:12px}.file-button{padding:10px 12px}.detail-toolbar{gap:7px}.detail-toolbar .btn-secondary,.detail-toolbar .btn-primary{font-size:11px;min-height:32px;padding:6px 9px}.detail-toolbar select{max-width:100%;width:100%;flex-basis:100%}.review-progress-label{flex-basis:100%;font-size:11px}.report-summary{padding:14px;font-size:12px}.workspace-controls{font-size:11px;gap:8px}.workspace-count-separator{margin:0 7px}.workspace-display-tools{display:none}.code-focus .file-panel,.code-focus .finding-panel{display:block}.code-scroll{min-height:250px;max-height:60vh}.finding-card{padding:16px}.finding-card dl{grid-template-columns:62px minmax(0,1fr)}.coverage-details li{display:block}.coverage-details li>span{display:block;max-width:100%;text-align:left;margin-top:4px}}

.report-export-section{margin-top:22px;border:1px solid var(--border-subtle);border-radius:8px;background:#fff;padding:17px 20px}.report-export-section>header{display:flex;align-items:center;justify-content:space-between;gap:16px}.report-export-section h2{font-size:13px;font-weight:650}.report-export-section header p{font-size:11px;color:var(--text-muted);margin-top:5px;line-height:1.7}.report-export-section header button{font-size:12px;white-space:nowrap;flex-shrink:0}.report-export-section .raw-report{margin-top:14px;font-size:11px}.report-export-section .raw-report pre{margin-top:12px;padding:12px;background:#f8f9fc}.report-export-section summary{cursor:pointer;color:var(--text-secondary)}@media(max-width:650px){.report-export-section{padding:15px}.report-export-section>header{align-items:flex-start;flex-wrap:wrap}.report-export-section header button{margin-left:auto}}
</style>
