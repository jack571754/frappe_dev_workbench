export function parseDiff(diff) {
  let old = 0, newer = 0, inHunk = false
  const lines = diff.split('\n'); if (lines.at(-1) === '') lines.pop()
  return lines.map(text => {
    const hunk = text.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
    if (hunk) { old = Number(hunk[1]); newer = Number(hunk[2]); inHunk = true; return { text, kind: 'hunk' } }
    if (!inHunk || text.startsWith('\\')) return { text, kind: 'hunk' }
    if (text.startsWith('-')) return { text, old: old++, kind: 'removed' }
    if (text.startsWith('+')) return { text, new: newer++, kind: 'added' }
    return { text, old: old++, new: newer++, kind: '' }
  })
}
