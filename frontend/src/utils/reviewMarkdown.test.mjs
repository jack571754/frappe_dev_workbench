import { strict as assert } from 'node:assert'
import { buildReviewMarkdown, reviewMarkdownFilename } from './reviewMarkdown.js'

const task = {
  title: '支付并发检查', repository: 'In_App_Purchasing_System', head_sha: 'a'.repeat(40),
  current_attempt: 'latest-attempt', status: 'failed', review_mode: 'scan', branch: 'master',
  attempt: { name: 'old-attempt', status: 'partial', tool_version: 'OpenCodeReview 1.13.2',
    started_at: '2026-10-22 13:00:00', finished_at: '2026-10-22 13:05:00',
    report: JSON.stringify({ summary: '发现竞态条件', partial: true,
      findings: [{ title: 'normalized issue', evidence: 'sample' }],
      coverage: { reviewed: ['api.py'], skipped: [{ path: 'large.py', reason: '超限' }] }, limitations: ['覆盖不足'] }),
    raw_report: JSON.stringify({ status: 'complete', comments: [
      { path: 'api.py', severity: 'critical', content: '缺少行锁\n可能重复扣款',
        start_line: 12, end_line: 14, existing_code: 'select()\n```\n<script>test</script>', suggestion_code: 'select_for_update()' },
    ] }),
  },
}
const md = buildReviewMarkdown(task)
assert.match(md, /^# 代码审查报告/m)
assert.match(md, /报告版本：old\\-attempt/)
assert.match(md, /执行状态：部分完成/)
assert.doesNotMatch(md, /执行状态：执行失败/)
assert.match(md, /历史报告/)
assert.match(md, /高风险/)
assert.match(md, /12–14/)
assert.match(md, /重复扣款/)
assert.match(md, /select_for_update\(\)/)
assert.ok(md.includes(String.raw`large\.py`))
assert.match(md, /覆盖不足/)
assert.ok(md.includes(task.attempt.raw_report), 'appendix must preserve raw output exactly')
assert.ok(md.includes('````text\nselect()\n```'), 'fence must contain embedded backticks safely')
assert.match(reviewMarkdownFilename(task), /^代码审查-In_App_Purchasing_System-aaaaaaaaaaaa-old-attempt\.md$/)

const many = structuredClone(task)
many.attempt.raw_report = JSON.stringify({ status: 'complete', comments: Array.from({ length: 201 }, (_, i) => ({ path: 'api.py', content: `finding ${i}`, severity: 'low' })) })
assert.match(buildReviewMarkdown(many), /finding 200/)
assert.match(buildReviewMarkdown(many), /201 项/)

const legacy = structuredClone(task)
legacy.attempt.report = JSON.stringify({ schema_version: 1, summary: 'Claude report', findings: [{ title: 'legacy issue', severity: 'medium', path: 'old.py', side: 'old', line: 3, end_line: 3, located: true, evidence: 'return data', suggestion: 'add check', trigger: 'empty input', impact: 'crash' }], coverage: { reviewed: ['old.py'], skipped: [] }, limitations: [] })
legacy.attempt.raw_report = 'not valid JSON\n```\nraw error'
assert.match(buildReviewMarkdown(legacy), /legacy issue/)
assert.match(buildReviewMarkdown(legacy), /旧版本/)
assert.ok(buildReviewMarkdown(legacy).includes(legacy.attempt.raw_report))

const unusual = structuredClone(task)
unusual.repository = '../bad:<repo>|?*'
unusual.attempt.name = 'x/y\r\nz'
assert.doesNotMatch(reviewMarkdownFilename(unusual), /[<>:"/\\|?*\x00-\x1f]/)
unusual.title = '<script>alert(1)</script> [link](https://example.invalid)'
unusual.attempt.raw_report = ''
const safe = buildReviewMarkdown(unusual).split('## 原始输出')[0]
assert.doesNotMatch(safe, /<script>/)
assert.doesNotMatch(safe, /\[link\]\(https/)

const empty = { title: 'empty', attempt: { name: 'empty', status: 'failed', raw_report: 'engine failed' } }
assert.match(buildReviewMarkdown(empty), /没有可读的问题列表/)
assert.doesNotMatch(buildReviewMarkdown(empty), /确认.*无问题/)
const long = structuredClone(task)
long.attempt.raw_report = '` '.repeat(150_000)
assert.doesNotThrow(() => buildReviewMarkdown(long))
console.log('Markdown export checks passed (history, 201 findings, fences, filenames, legacy and empty reports)')
