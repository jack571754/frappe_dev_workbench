// Copyright (c) 2026, Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project', {
	refresh: function(frm) {
		// Frappe's default is "title - docname", which repeats our project name.
		// Keep the workspace identity while retaining the actual project label.
		const projectTitle = frm.is_new()
			? __('新建项目')
			: (frm.doc.project_name || frm.doc.name || __('项目配置'));
		frappe.utils.set_title(`${projectTitle} - ${__('研发工作台')}`);

		frm.add_custom_button(__('打开研发工作台看板'), function() {
			window.open('/dev-workbench', '_blank');
		}, __('快捷导航'));

		if (!frm.is_new()) {
			frm.add_custom_button(__('添加关联代码库'), function() {
				frappe.prompt([
					{
						fieldname: 'repository',
						fieldtype: 'Link',
						label: __('选择代码库'),
						options: 'Codeup Repository',
						reqd: 1,
					}
				], function(values) {
					let row = frm.add_child('project_repositories', {
						repository: values.repository
					});
					frm.refresh_field('project_repositories');
					frm.save();
				}, __('关联代码库'));
			});
		}
	}
});
