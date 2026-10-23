import { api } from '@/utils/api'

const prefix = '/api/method/dev_workbench.api.v1.code_review.'
export async function reviewApi(method, params = {}, write = false) {
  const response = write
    ? await api.post(prefix + method, params)
    : await api.get(prefix + method + '?' + new URLSearchParams(params))
  const data = await response.json()
  return data.message
}

export const repositoryStateLabels = {
  ready: '已就绪', unavailable: '路径不可用', not_configured: '未配置', offline: '执行端未就绪',
}
export function formatReportTime(value, fallback = '—') {
  if (!value) return fallback
  const time = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(time.getTime())) return String(value)
  const pad = number => String(number).padStart(2, '0')
  return `${time.getMonth() + 1}-${pad(time.getDate())} ${pad(time.getHours())}:${pad(time.getMinutes())}`
}
export const states = {
  queued: '等待执行', preparing: '准备代码', running: 'AI 审查中', completed: 'AI 审查完成',
  partial: '部分完成', failed: '执行失败', cancelled: '已取消', interrupted: '已中断',
}
export const reviewStates = { pending: '未复核', in_progress: '复核中', completed: '已复核' }
export const severityLabels = { high: '高风险', medium: '中风险', low: '低风险', suggestion: '建议' }
export const decisionLabels = { pending: '待确认', confirmed: '已确认', ignored: '已忽略' }
export const activeStates = ['queued', 'preparing', 'running']
export function parseJson(value, fallback = {}) {
  try { return typeof value === 'string' ? JSON.parse(value) : value || fallback } catch { return fallback }
}

export function feedbackText(task, findings) {
  return findings.filter(f => f.decision === 'confirmed').map((f, i) =>
    `${i + 1}. [${severityLabels[f.severity]}] ${f.title}\n仓库：${task.repository}\n提交：${task.head_sha}\n位置：${f.path}${f.located ? `:${f.line} (${f.side === 'old' ? '旧版本' : '新版本'})` : '（未定位）'}\n触发条件：${f.trigger}\n影响：${f.impact}\n依据：${f.evidence}\n建议：${f.suggestion}${f.note ? '\n备注：' + f.note : ''}`
  ).join('\n\n')
}
