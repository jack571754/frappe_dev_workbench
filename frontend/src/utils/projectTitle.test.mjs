import { strict as assert } from 'node:assert'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'
const source = await readFile(new URL('../../../dev_workbench/dev_workbench/doctype/project/project.js', import.meta.url), 'utf8')
let events, title
vm.runInNewContext(source, {
  frappe: { ui: { form: { on(doctype, handlers) { assert.equal(doctype, 'Project'); events = handlers } } },
    utils: { set_title(value) { title = value } } },
  __(text) { return text },
})
function refresh(doc, isNew = false) {
  title = undefined
  events.refresh({ doc, is_new() { return isNew }, add_custom_button() {} })
  return title
}
assert.equal(refresh({ name: 'VisionForge视觉工场', project_name: 'VisionForge视觉工场' }), 'VisionForge视觉工场 - 研发工作台')
assert.equal(refresh({ name: 'internal-id', project_name: '项目显示名称' }), '项目显示名称 - 研发工作台')
assert.equal(refresh({ name: 'Project-001' }), 'Project-001 - 研发工作台')
assert.equal(refresh({}, true), '新建项目 - 研发工作台')
console.log('Project title branding checks passed')
