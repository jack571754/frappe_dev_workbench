import { strict as assert } from 'node:assert'
import { matchesReviewView, reviewSummary, emptyReviewMessage } from './reviewPresentation.js'
for (const status of ['failed', 'cancelled', 'interrupted']) {
  assert.match(emptyReviewMessage(status, {}), /未完成/)
  assert.doesNotMatch(emptyReviewMessage(status, {}), /未发现问题/)
}
assert.match(emptyReviewMessage('running', {}), /正在审查/)
assert.match(emptyReviewMessage('partial', { schema_version: 1, partial: true }), /其余内容/)
assert.match(emptyReviewMessage('completed', { schema_version: 1 }), /未发现问题/)
const tasks = [
  { status: 'completed', review_status: 'pending', pending_count: 0 },
  { status: 'partial', review_status: 'in_progress', pending_count: 10 },
  { status: 'completed', review_status: 'completed', pending_count: 0 },
  { status: 'queued', review_status: 'pending', pending_count: 0 },
  { status: 'running', review_status: 'pending', pending_count: 0 },
  { status: 'failed', review_status: 'pending', pending_count: 0 },
  { status: 'cancelled', review_status: 'pending', pending_count: 0 },
]
assert.deepEqual(reviewSummary(tasks), { pending: 2, running: 2, failed: 1, issues: 10 })
assert.equal(matchesReviewView(tasks[2], 'pending'), false)
assert.equal(matchesReviewView(tasks[0], 'pending'), true)
assert.equal(matchesReviewView(tasks[6], 'failed'), false)
console.log('review presentation checks passed')
