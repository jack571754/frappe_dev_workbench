// Copyright (c) 2026, Company and contributors
// For license information, please see license.txt

const DEFAULT_EXCLUDE_RULES = `*.lock
package-lock.json
yarn.lock
pnpm-lock.yaml
dist/**
build/**
public/**
*.min.js
node_modules/**`;

frappe.ui.form.on('Codeup Repository', {
	refresh: function(frm) {
		frm.add_custom_button(__('重置为默认排除规则'), function() {
			frappe.confirm(__('确定要将排除规则重置为系统默认配置吗？'), function() {
				frm.set_value('exclude_rules', DEFAULT_EXCLUDE_RULES);
				frappe.show_alert({
					message: __('已恢复默认排除规则，请点击保存生效'),
					indicator: 'green'
				});
			});
		}, __('工具'));

		if (!frm.is_new()) {
			frm.add_custom_button(__('测试连通性'), function() {
				frappe.show_alert({
					message: __('代码库配置有效: ') + frm.doc.repository_name,
					indicator: 'blue'
				});
			}, __('工具'));
		}
	}
});
