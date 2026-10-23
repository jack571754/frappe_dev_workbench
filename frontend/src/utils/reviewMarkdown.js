const severityLabels = { critical: '高风险', high: '高风险', medium: '中风险', low: '低风险', suggestion: '建议' }
const statusLabels = { queued: '等待执行', preparing: '准备代码', running: 'AI 审查中', completed: 'AI 审查完成', partial: '部分完成', failed: '执行失败', cancelled: '已取消', interrupted: '已中断' }

function object(value) {
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch { return {} }
}

function value(text) { return text == null ? '' : String(text) }

// Report prose is untrusted model/repository text. Keep it literal in Markdown.
function prose(text) {
  return value(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/[\\`*_{}\[\]()#+.!|~\-]/g, '\\$&')
}

function fence(text, language = 'text') {
  const raw = value(text)
  const longest = (raw.match(/`+/g) || []).reduce((max, run) => Math.max(max, run.length), 0)
  const delimiter = '`'.repeat(Math.max(3, longest + 1))
  return `${delimiter}${language}\n${raw}${raw.endsWith('\n') ? '' : '\n'}${delimiter}`
}

function paragraph(label, text) {
  return `**${label}**\n\n${prose(text || '未说明')}\n`
}

function findingsFor(report, raw) {
  if (Array.isArray(raw.comments)) {
    return raw.comments.map(comment => ({
      title: value(comment.content).split('\n')[0],
      severity: ['style', 'documentation', 'maintainability'].includes(comment.category) ? 'suggestion' : comment.severity,
      path: comment.path, side: 'new', line: comment.start_line, end_line: comment.end_line,
      impact: comment.content, evidence: comment.existing_code, suggestion: comment.suggestion_code,
    }))
  }
  // Claude and older executions already have a normalized report saved with the attempt.
  const source = Array.isArray(report.findings) ? report : object(raw.structured_output)
  return Array.isArray(source.findings) ? source.findings : []
}

export function buildReviewMarkdown(task) {
  const attempt = task.attempt || {}
  const report = object(attempt.report)
  const rawText = value(attempt.raw_report)
  const raw = object(rawText)
  const findings = findingsFor(report, raw)
  const historical = !!attempt.name && !!task.current_attempt && attempt.name !== task.current_attempt
  const state = attempt.status || '未知'
  const lines = [
    '# 代码审查报告', '',
    `- 任务：${prose(task.title || '代码审查')}`,
    `- 仓库：${prose(task.repository || '未提供')}`,
    `- 审查方式：${task.review_mode === 'scan' ? '全项目扫描' : '提交审查'}`,
    ...(task.branch ? [`- 分支：${prose(task.branch)}`] : []),
    `- 提交 SHA：${prose(task.head_sha || '未提供')}`,
    ...(task.base_sha ? [`- 父提交 SHA：${prose(task.base_sha)}`] : []),
    `- 报告版本：${prose(attempt.name || '未提供')}${historical ? '（历史报告）' : ''}`,
    `- 执行状态：${statusLabels[state] || prose(state)}`,
    `- 审查引擎：${prose(attempt.tool_version || '未提供')}`,
    `- 开始时间：${prose(attempt.started_at || '未提供')}`,
    `- 完成时间：${prose(attempt.finished_at || '未提供')}`,
    '', '> AI 审查发现为候选问题，需人工核实。', '',
    '## 审查摘要', '', prose(report.summary || raw.project_summary || '工具未提供可读摘要。'), '',
  ]
  if (report.partial || state === 'partial') lines.push('> 本报告为部分审查，不能据此认定全部代码均无问题。', '')
  if (attempt.error) lines.push(paragraph('执行说明', attempt.error))
  lines.push(`## 审查发现（${findings.length} 项）`, '')
  if (!findings.length) lines.push('本报告没有可读的问题列表，请结合覆盖说明与原始输出判断。', '')
  findings.forEach((finding, index) => {
    const severity = severityLabels[finding.severity] || '未标注风险'
    const path = value(finding.path) || '未提供文件路径'
    const validLocation = finding.located !== false && Number.isInteger(finding.line) && finding.line > 0
    const location = validLocation ? `:${finding.line}${Number.isInteger(finding.end_line) && finding.end_line > finding.line ? `–${finding.end_line}` : ''}` : '（未定位）'
    const side = finding.side === 'old' ? '旧版本' : '新版本'
    lines.push(`### ${index + 1}. [${severity}] ${prose(finding.title || '候选问题')}`, '',
      `- 代码位置：${prose(path)}${location} · ${side}`, '',
      paragraph('触发条件', finding.trigger), paragraph('影响 / 问题说明', finding.impact),
      '**代码依据**', '', finding.evidence ? fence(finding.evidence) : '未提供', '',
      '**修改建议**', '', finding.suggestion ? fence(finding.suggestion) : '未提供', '')
    if (finding.uncertainty) lines.push(paragraph('尚待核实', finding.uncertainty))
  })
  lines.push('## 覆盖范围与限制', '')
  const coverage = object(report.coverage)
  const reviewed = Array.isArray(coverage.reviewed) ? coverage.reviewed : []
  const skipped = Array.isArray(coverage.skipped) ? coverage.skipped : []
  lines.push(`有完成凭据：${reviewed.length} 个文件；跳过或未确认覆盖：${skipped.length} 个文件。`, '')
  if (!Object.keys(coverage).length) lines.push('工具未提供覆盖范围，不能确认全部文件已经审查。', '')
  if (reviewed.length) lines.push('### 有完成凭据的文件', '', ...reviewed.map(path => `- ${prose(path)}`), '')
  if (skipped.length) lines.push('### 跳过或未确认覆盖的文件', '', ...skipped.map(item => `- ${prose(item.path)}：${prose(item.reason || '未说明原因')}`), '')
  if (Array.isArray(report.limitations) && report.limitations.length) lines.push('### 限制说明', '', ...report.limitations.map(text => `- ${prose(text)}`), '')
  lines.push('## 原始输出', '', rawText ? fence(rawText, Object.keys(raw).length ? 'json' : 'text') : '该版本未保存原始输出。', '')
  return lines.join('\n')
}

export function reviewMarkdownFilename(task) {
  const clean = (text, length) => value(text).replace(/[<>:"/\\|?*\x00-\x1f\x7f]/g, '_').replace(/\s+/g, '_').replace(/[. ]+$/g, '').slice(0, length)
  const repository = clean(task.repository, 70) || 'repository'
  const sha = clean(task.head_sha, 12) || 'unknown'
  const version = clean(task.attempt?.name || task.attempt?.started_at, 50) || 'report'
  return `代码审查-${repository}-${sha}-${version}.md`
}
