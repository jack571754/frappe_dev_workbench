export function matchesReviewView(task, view) {
  if (view === 'pending') return ['completed', 'partial'].includes(task.status) && task.review_status !== 'completed'
  if (view === 'running') return ['queued', 'preparing', 'running'].includes(task.status)
  if (view === 'failed') return ['failed', 'interrupted'].includes(task.status)
  return true
}
export function reviewSummary(tasks) {
  return {
    pending: tasks.filter(t => matchesReviewView(t, 'pending')).length,
    running: tasks.filter(t => matchesReviewView(t, 'running')).length,
    failed: tasks.filter(t => matchesReviewView(t, 'failed')).length,
    issues: tasks.filter(t => matchesReviewView(t, 'pending')).reduce((n, t) => n + (Number(t.pending_count) || 0), 0),
  }
}
export function emptyReviewMessage(status, report = {}) {
  if (['queued', 'preparing', 'running'].includes(status)) return 'AI 正在审查，问题将在报告返回后显示。'
  if (['failed', 'interrupted', 'cancelled'].includes(status) || !report.schema_version) return '审查未完成，暂无可用结论。请查看执行状态及错误提示。'
  if (report.partial) return '已覆盖部分未发现问题，其余内容需人工检查。'
  return 'AI 未发现问题，仍需你确认完成复核。'
}

