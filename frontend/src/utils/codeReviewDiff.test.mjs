import { strict as assert } from 'node:assert'
import { parseDiff } from './codeReviewDiff.js'

const rows = parseDiff('--- a/test.js\n+++ b/test.js\n@@ -1,2 +1,2 @@\n---counter\n+++counter\n next()\n')
assert.equal(rows[3].old, 1)
assert.equal(rows[4].new, 1)
assert.equal(rows[5].old, 2)
assert.equal(rows[5].new, 2)
console.log('diff regression passed')
